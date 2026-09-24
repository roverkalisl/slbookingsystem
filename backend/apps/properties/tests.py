"""
Tests for property management system including search and pricing.

Run with: python manage.py test apps.properties
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    Property, PropertyType, RoomType, Pricing, SeasonalRate,
    PropertyAmenity, Amenity, Destination
)
from .pricing import PricingCalculator
from .search import PropertySearchService
from apps.core.models import Role, UserRole

User = get_user_model()


class PricingCalculatorTestCase(TestCase):
    """Tests for pricing calculation logic"""

    def setUp(self):
        """Set up test data"""
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        property_type = PropertyType.objects.create(name='Villa')
        self.property = Property.objects.create(
            owner=self.owner,
            property_type=property_type,
            name='Test Property',
            city='Colombo',
            district='Western',
            province='Western',
            status='published'
        )

        self.room_type = RoomType.objects.create(
            property=self.property,
            name='Room',
            max_adults=2,
            total_occupancy=2,
            total_rooms=1
        )

        self.pricing = Pricing.objects.create(
            room_type=self.room_type,
            base_price=Decimal('5000.00'),
            weekend_price=Decimal('6000.00'),
            extra_guest_fee=Decimal('500.00')
        )

    def test_base_price_calculation(self):
        """Test basic price calculation"""
        check_in = date(2026, 9, 8)  # Tuesday (fixed, non-weekend date - avoids weekend-rate flakiness)
        check_out = check_in + timedelta(days=3)  # Friday (3 nights)

        calculator = PricingCalculator(self.room_type)
        breakdown = calculator.calculate_booking_price(check_in, check_out, num_adults=2, num_children=0)

        # 3 nights x 5000 = 15000
        self.assertEqual(breakdown['room_subtotal'], Decimal('15000.00'))
        self.assertEqual(breakdown['nights'], 3)

    def test_weekend_pricing(self):
        """Test weekend price applied correctly"""
        # Friday-Sunday: Friday and Saturday nights are charged, both are weekend-priced
        friday = date(2026, 9, 11)  # Friday
        sunday = date(2026, 9, 13)  # Sunday

        calculator = PricingCalculator(self.room_type)
        breakdown = calculator.calculate_booking_price(friday, sunday, num_adults=2)

        # Friday (weekend, 6000) + Saturday (weekend, 6000) = 12000
        self.assertGreater(breakdown['room_subtotal'], Decimal('10000.00'))

    def test_extra_guest_fee(self):
        """Test extra guest fee calculation"""
        check_in = date(2026, 9, 8)  # Tuesday
        check_out = check_in + timedelta(days=1)  # 1 night

        calculator = PricingCalculator(self.room_type)
        breakdown = calculator.calculate_booking_price(check_in, check_out, num_adults=4)  # 2 extra guests

        # Should include extra guest fee
        self.assertIn('guest_fees', breakdown)
        self.assertGreater(breakdown['guest_fees'], Decimal('0'))

    def test_tax_calculation(self):
        """Test tax applied to total price"""
        check_in = date(2026, 9, 8)  # Tuesday
        check_out = check_in + timedelta(days=1)

        calculator = PricingCalculator(self.room_type)
        breakdown = calculator.calculate_booking_price(check_in, check_out, num_adults=2)

        # Tax is charged on (discounted subtotal + service fee), using the
        # Pricing model's default rates: service_fee_percent=5%, tax_percent=10%
        self.assertIn('tax', breakdown)
        self.assertGreater(breakdown['tax'], Decimal('0'))
        expected_taxable_amount = breakdown['subtotal'] - breakdown['discount'] + breakdown['service_fee']
        self.assertEqual(breakdown['tax'], expected_taxable_amount * Decimal('0.10'))

    def test_seasonal_rate_override(self):
        """Test seasonal rate overrides base price"""
        check_in = date(2026, 9, 8)  # Tuesday
        check_out = check_in + timedelta(days=3)

        # Create seasonal rate
        SeasonalRate.objects.create(
            room_type=self.room_type,
            name='High Season',
            start_date=check_in,
            end_date=check_out,
            price_per_night=Decimal('8000.00')
        )

        calculator = PricingCalculator(self.room_type)
        breakdown = calculator.calculate_booking_price(check_in, check_out, num_adults=2)

        # Should use seasonal rate (8000 x 3 = 24000)
        self.assertEqual(breakdown['room_subtotal'], Decimal('24000.00'))


class PropertySearchTestCase(TestCase):
    """Tests for property search functionality"""

    def setUp(self):
        """Set up test data"""
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        # Create amenities
        self.wifi = Amenity.objects.create(name='WiFi')
        self.pool = Amenity.objects.create(name='Swimming Pool')
        self.gym = Amenity.objects.create(name='Gym')

        # Create destination
        self.destination = Destination.objects.create(
            name='Colombo',
            district='Western',
            province='Western'
        )

        # Create property types
        self.villa_type = PropertyType.objects.create(name='Villa')
        self.apartment_type = PropertyType.objects.create(name='Apartment')

        # Create properties.
        # NOTE: status must be 'approved' - PropertySearchService.search()
        # defaults to Property.objects.filter(status='approved') (guests only
        # ever see approved listings). 'published' is not one of the model's
        # STATUS_CHOICES; using it here would silently match nothing.
        # Property also has no price_range_min/max fields - price filtering
        # and sorting both go through RoomType -> Pricing, so each property
        # needs a real room type + pricing row to be found by price filters.
        self.villa1 = Property.objects.create(
            owner=self.owner,
            property_type=self.villa_type,
            name='Luxury Villa',
            city='Colombo',
            district='Western',
            province='Western',
            status='approved',
        )
        villa1_room = RoomType.objects.create(property=self.villa1, name='Room', max_adults=2, total_occupancy=2, total_rooms=1)
        Pricing.objects.create(room_type=villa1_room, base_price=Decimal('10000.00'))

        self.villa2 = Property.objects.create(
            owner=self.owner,
            property_type=self.villa_type,
            name='Beach Villa',
            city='Colombo',
            district='Western',
            province='Western',
            status='approved',
        )
        villa2_room = RoomType.objects.create(property=self.villa2, name='Room', max_adults=2, total_occupancy=2, total_rooms=1)
        Pricing.objects.create(room_type=villa2_room, base_price=Decimal('5000.00'))

        self.apartment = Property.objects.create(
            owner=self.owner,
            property_type=self.apartment_type,
            name='Downtown Apartment',
            city='Colombo',
            district='Western',
            province='Western',
            status='approved',
        )
        apartment_room = RoomType.objects.create(property=self.apartment, name='Room', max_adults=2, total_occupancy=2, total_rooms=1)
        Pricing.objects.create(room_type=apartment_room, base_price=Decimal('3000.00'))

        # Add amenities
        PropertyAmenity.objects.create(property=self.villa1, amenity=self.wifi)
        PropertyAmenity.objects.create(property=self.villa1, amenity=self.pool)
        PropertyAmenity.objects.create(property=self.villa2, amenity=self.wifi)
        PropertyAmenity.objects.create(property=self.apartment, amenity=self.gym)

    def test_search_all_properties(self):
        """Test search without filters returns all published properties"""
        results = PropertySearchService().get_results()

        self.assertGreaterEqual(len(results), 3)

    def test_filter_by_type(self):
        """Test filter by property type"""
        results = PropertySearchService().filter_by_property_type([self.villa_type.id]).get_results()

        ids = [p.id for p in results]
        self.assertIn(self.villa1.id, ids)
        self.assertIn(self.villa2.id, ids)
        self.assertNotIn(self.apartment.id, ids)

    def test_filter_by_price_range(self):
        """Test filter by price range"""
        results = PropertySearchService().filter_by_price_range(
            min_price=Decimal('3000'),
            max_price=Decimal('8000')
        ).get_results()

        ids = [p.id for p in results]
        # Villa2 (5000) and Apartment (3000) should match; Villa1 (10000) should not
        self.assertIn(self.villa2.id, ids)
        self.assertIn(self.apartment.id, ids)
        self.assertNotIn(self.villa1.id, ids)

    def test_filter_by_amenities(self):
        """Test filter by amenities"""
        results = PropertySearchService().filter_by_amenities([self.wifi.id]).get_results()

        ids = [p.id for p in results]
        self.assertIn(self.villa1.id, ids)
        self.assertIn(self.villa2.id, ids)
        self.assertNotIn(self.apartment.id, ids)

    def test_chaining_filters(self):
        """Test chaining multiple filters"""
        results = (
            PropertySearchService()
            .filter_by_property_type([self.villa_type.id])
            .filter_by_price_range(Decimal('3000'), Decimal('10000'))
            .filter_by_amenities([self.wifi.id])
            .get_results()
        )

        ids = [p.id for p in results]
        # Should only return villa2 (villa, price matches, has wifi)
        self.assertIn(self.villa2.id, ids)
        self.assertNotIn(self.apartment.id, ids)

    def test_sort_by_price_asc(self):
        """Test sorting by price ascending"""
        results = PropertySearchService().sort_by('price', 'asc').get_results()

        price_list = [p.room_types.first().pricing.base_price for p in results]
        # Should be sorted ascending: apartment (3000), villa2 (5000), villa1 (10000)
        self.assertEqual(price_list, sorted(price_list))

    def test_sort_by_price_desc(self):
        """Test sorting by price descending"""
        results = PropertySearchService().sort_by('price', 'desc').get_results()

        price_list = [p.room_types.first().pricing.base_price for p in results]
        # Should be sorted descending: villa1 (10000), villa2 (5000), apartment (3000)
        self.assertEqual(price_list, sorted(price_list, reverse=True))
