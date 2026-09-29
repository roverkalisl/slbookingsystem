"""
One-off / repair: recalculate every property's stored public rating
(Property.average_rating, total_reviews) from its eligible reviews
(apps.reviews.ratings). New changes are kept in sync automatically by the
Review signals - this only fixes values stored before that existed.

    python manage.py sync_review_ratings --dry-run   # report only, change nothing
    python manage.py sync_review_ratings

Non-destructive: reviews are never modified; only the two rating fields of
properties whose stored values are wrong are updated.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.properties.models import Property
from apps.reviews.ratings import public_rating, sync_property_rating


class Command(BaseCommand):
    help = 'Recalculate Property.average_rating / total_reviews from eligible public reviews.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report what would change, then roll back.')

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        changed = 0
        for prop in Property.objects.order_by('name').only('id', 'name', 'average_rating', 'total_reviews'):
            average, count = public_rating(prop.pk)
            before = (prop.average_rating, prop.total_reviews)
            if sync_property_rating(prop.pk):
                changed += 1
                self.stdout.write(f'{prop.name}: {before[0]} ({before[1]} reviews) -> '
                                  f'{average if average is not None else 0} ({count} reviews)')
        self.stdout.write(self.style.SUCCESS(f'{changed} propert{"y" if changed == 1 else "ies"} updated.'))
        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('DRY RUN: rolled back - nothing was saved.'))
