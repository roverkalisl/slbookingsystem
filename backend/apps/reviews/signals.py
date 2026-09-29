"""
Keep Property.average_rating / total_reviews in sync with the property's
public reviews whenever a review is created, changed (rating, published,
flagged) or deleted - through the API, Django admin, or a cascade.
"""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Review
from .ratings import sync_property_rating


@receiver(pre_save, sender=Review)
def remember_previous_property(sender, instance, raw=False, **kwargs):
    # If a review ever moves to another property, the old one must be recalculated too
    instance._previous_property_id = None
    if not raw and instance.pk:
        instance._previous_property_id = (
            Review.objects.filter(pk=instance.pk).values_list('property_id', flat=True).first()
        )


@receiver(post_save, sender=Review)
def sync_rating_after_save(sender, instance, raw=False, **kwargs):
    if raw:  # loaddata fixtures
        return
    sync_property_rating(instance.property_id)
    previous = getattr(instance, '_previous_property_id', None)
    if previous and previous != instance.property_id:
        sync_property_rating(previous)


@receiver(post_delete, sender=Review)
def sync_rating_after_delete(sender, instance, **kwargs):
    sync_property_rating(instance.property_id)
