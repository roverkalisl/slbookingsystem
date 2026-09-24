"""
Signal handlers for the core app.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Ensure every User has a UserProfile, regardless of how the User was
    created (registration API, Django admin, createsuperuser, shell, etc.).
    Previously this only happened inside RegisterSerializer.create(), so any
    other creation path left user.profile raising RelatedObjectDoesNotExist.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)
