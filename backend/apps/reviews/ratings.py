"""
Public property rating - the ONE definition of which reviews count.

Used by both:
- the stored Property.average_rating / total_reviews shown on the property
  page (kept in sync by the Review signals in apps/reviews/signals.py), and
- the Schema.org aggregateRating in the property JSON-LD (config/seo.py),
so the visible rating and the structured-data rating can never disagree.

A review counts when it is published, not flagged, and has a valid 1-5
overall rating. Deleted reviews are gone from the table, so never counted.
"""

from decimal import Decimal

from django.db.models import Avg, Count

MIN_RATING = 1
MAX_RATING = 5


def public_reviews(property_id):
    """Reviews that count towards a property's public rating."""
    from .models import Review

    return Review.objects.filter(
        property_id=property_id,
        is_published=True,
        is_flagged=False,
        overall_rating__gte=MIN_RATING,
        overall_rating__lte=MAX_RATING,
    )


def public_rating(property_id):
    """
    (average, count) of the eligible reviews. The average is rounded to one
    decimal - the precision shown on the page and published in JSON-LD - and
    is None when there are no eligible reviews.
    """
    stats = public_reviews(property_id).aggregate(count=Count('id'), average=Avg('overall_rating'))
    if not stats['count'] or stats['average'] is None:
        return None, 0
    return round(float(stats['average']), 1), stats['count']


def sync_property_rating(property_id) -> bool:
    """
    Store the public rating on the property (0 / 0 when there are no eligible
    reviews). Writes only when a value actually changes; returns True if it did.
    A queryset update, so Property.updated_at (sitemap lastmod) is not touched.
    """
    from apps.properties.models import Property

    average, count = public_rating(property_id)
    average_value = Decimal(str(average)) if average is not None else Decimal('0')
    changed = (
        Property.objects.filter(pk=property_id)
        .exclude(average_rating=average_value, total_reviews=count)
        .update(average_rating=average_value, total_reviews=count)
    )
    return bool(changed)
