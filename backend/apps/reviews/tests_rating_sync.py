"""
Property.average_rating / total_reviews stay in sync with the property's
public reviews (apps.reviews.ratings + signals), and match the JSON-LD
aggregateRating exactly.

Run with: python manage.py test apps.reviews.tests_rating_sync
"""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.properties.models import Property, PropertyType, RoomType
from apps.reviews.models import Review
from config.seo import property_json_ld

User = get_user_model()


class RatingSyncTestBase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='rs-owner@example.com', password='x')
        self.guest = User.objects.create_user(email='rs-guest@example.com', password='x')
        ptype = PropertyType.objects.create(name='RS Hotel')
        self.prop = Property.objects.create(owner=self.owner, property_type=ptype, name='Rated Villa', description='d',
                                            city='Galle', district='Galle', province='Southern', status='approved')
        self.room = RoomType.objects.create(property=self.prop, name='Room', max_adults=2, total_occupancy=2, total_rooms=5)
        self.seq = 0

    def review(self, rating, published=True, flagged=False, prop=None):
        prop = prop or self.prop
        self.seq += 1
        check_in = date.today() - timedelta(days=10)
        booking = Booking.objects.create(
            booking_reference=f'RS-{self.seq}', property=prop, room_type=prop.room_types.first() or self.room,
            guest=self.guest, check_in_date=check_in, check_out_date=check_in + timedelta(days=1), number_of_nights=1,
            number_of_adults=1, room_price=Decimal('1'), subtotal=Decimal('1'), total_price=Decimal('1'), status='completed')
        return Review.objects.create(booking=booking, property=prop, guest=self.guest, overall_rating=rating,
                                     comment='c', is_published=published, is_flagged=flagged)

    def stored(self, prop=None):
        prop = prop or self.prop
        prop.refresh_from_db()
        return prop.average_rating, prop.total_reviews

    def assertStored(self, average, count, prop=None):
        self.assertEqual(self.stored(prop), (Decimal(average), count))

    def assertMatchesJsonLd(self, prop=None):
        """The visible (stored) rating and the JSON-LD aggregateRating are the same values."""
        prop = prop or self.prop
        average, count = self.stored(prop)
        rating = property_json_ld(prop).get('aggregateRating')
        if count == 0:
            self.assertIsNone(rating)
            self.assertEqual(average, Decimal('0'))
        else:
            self.assertEqual((Decimal(str(rating['ratingValue'])), rating['reviewCount']), (average, count))


class RatingSyncTestCase(RatingSyncTestBase):
    def test_1_no_reviews(self):
        self.assertStored('0', 0)
        self.assertMatchesJsonLd()

    def test_2_one_published_five_star_review(self):
        self.review(5)
        self.assertStored('5.0', 1)
        self.assertMatchesJsonLd()

    def test_3_two_published_reviews_are_averaged(self):
        self.review(5)
        self.review(4)
        self.assertStored('4.5', 2)
        self.assertMatchesJsonLd()

    def test_average_is_rounded_like_the_page_and_json_ld(self):
        for rating in (5, 4, 4):  # 4.333...
            self.review(rating)
        self.assertStored('4.3', 3)
        self.assertMatchesJsonLd()

    def test_4_unpublished_review_is_not_counted(self):
        self.review(5)
        self.review(1, published=False)
        self.assertStored('5.0', 1)
        self.assertMatchesJsonLd()

    def test_5_flagged_review_is_not_counted(self):
        self.review(5)
        self.review(1, flagged=True)
        self.assertStored('5.0', 1)
        self.assertMatchesJsonLd()

    def test_invalid_rating_is_not_counted(self):
        self.review(5)
        self.review(0)
        self.review(9)
        self.assertStored('5.0', 1)
        self.assertMatchesJsonLd()

    def test_6_updating_a_review_updates_the_rating(self):
        review = self.review(5)
        self.review(3)
        self.assertStored('4.0', 2)
        review.overall_rating = 1
        review.save()
        self.assertStored('2.0', 2)
        self.assertMatchesJsonLd()

    def test_7_deleting_a_review_updates_the_rating(self):
        keep = self.review(4)
        gone = self.review(2)
        self.assertStored('3.0', 2)
        gone.delete()
        self.assertStored('4.0', 1)
        self.assertMatchesJsonLd()
        keep.delete()
        self.assertStored('0', 0)
        self.assertMatchesJsonLd()

    def test_deleting_the_booking_cascades_and_updates_the_rating(self):
        review = self.review(2)
        self.review(4)
        review.booking.delete()
        self.assertStored('4.0', 1)

    def test_8_publishing_and_unpublishing_update_the_rating(self):
        review = self.review(1, published=False)
        self.review(5)
        self.assertStored('5.0', 1)
        review.is_published = True
        review.save()
        self.assertStored('3.0', 2)
        self.assertMatchesJsonLd()
        review.is_published = False
        review.save()
        self.assertStored('5.0', 1)
        self.assertMatchesJsonLd()

    def test_flagging_and_unflagging_update_the_rating(self):
        review = self.review(1)
        self.review(5)
        review.is_flagged = True
        review.save()
        self.assertStored('5.0', 1)
        review.is_flagged = False
        review.save()
        self.assertStored('3.0', 2)
        self.assertMatchesJsonLd()

    def test_other_properties_are_not_affected(self):
        other = Property.objects.create(owner=self.owner, property_type=self.prop.property_type, name='Other',
                                        description='d', city='Ella', district='Badulla', province='Uva', status='approved')
        RoomType.objects.create(property=other, name='R', max_adults=2, total_occupancy=2, total_rooms=1)
        self.review(2, prop=other)
        self.review(5)
        self.assertStored('5.0', 1)
        self.assertStored('2.0', 1, prop=other)

    def test_unchanged_values_cause_no_write(self):
        from apps.reviews.ratings import sync_property_rating
        self.review(4)
        self.assertFalse(sync_property_rating(self.prop.pk))  # already correct -> no UPDATE

    def test_rating_sync_does_not_touch_property_updated_at(self):
        before = Property.objects.get(pk=self.prop.pk).updated_at
        self.review(5)
        self.assertEqual(Property.objects.get(pk=self.prop.pk).updated_at, before)


class ReviewApiSyncTestCase(APITestCase, RatingSyncTestBase):
    """The real review workflow (POST /api/reviews/) triggers the sync."""

    def test_review_created_through_the_api_updates_the_property(self):
        check_in = date.today() - timedelta(days=5)
        booking = Booking.objects.create(
            booking_reference='RS-API', property=self.prop, room_type=self.room, guest=self.guest,
            check_in_date=check_in, check_out_date=check_in + timedelta(days=2), number_of_nights=2,
            number_of_adults=2, room_price=Decimal('1'), subtotal=Decimal('2'), total_price=Decimal('2'), status='completed')
        self.client.force_authenticate(self.guest)
        response = self.client.post('/api/reviews/', {'booking_id': str(booking.id), 'rating': 4, 'comment': 'Nice'},
                                    format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertStored('4.0', 1)
        self.assertMatchesJsonLd()


class SyncCommandTestCase(RatingSyncTestBase):
    def test_command_repairs_stale_stored_values_and_dry_run_changes_nothing(self):
        self.review(5)
        self.review(4)
        Property.objects.filter(pk=self.prop.pk).update(average_rating=Decimal('1.00'), total_reviews=99)  # stale

        out = StringIO()
        call_command('sync_review_ratings', '--dry-run', stdout=out)
        self.assertIn('Rated Villa: 1.00 (99 reviews) -> 4.5 (2 reviews)', out.getvalue())
        self.assertStored('1.00', 99)  # rolled back

        call_command('sync_review_ratings', stdout=StringIO())
        self.assertStored('4.5', 2)
        self.assertEqual(Review.objects.count(), 2)  # reviews untouched
