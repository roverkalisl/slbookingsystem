"""
Data migration: book "Entry Villa" properties as a whole unit.

Matches the property type by NAME (case-insensitive) - never by database id -
and only changes its booking_mode. The type's id and name are untouched, and
no property, room or booking row is modified: existing Entry Villa listings
get their system-managed "Entire Villa" unit the first time the owner saves
Villa Details (see PropertyViewSet.villa), which deactivates - never deletes -
any legacy owner-created rooms.

If no "Entry Villa" type exists (e.g. a fresh database), this is a no-op.
"""

from django.db import migrations

ENTRY_VILLA_NAME = 'Entry Villa'


def set_entry_villa_whole_property(apps, schema_editor):
    PropertyType = apps.get_model('properties', 'PropertyType')
    PropertyType.objects.filter(name__iexact=ENTRY_VILLA_NAME).update(booking_mode='whole_property')


def unset_entry_villa_whole_property(apps, schema_editor):
    PropertyType = apps.get_model('properties', 'PropertyType')
    PropertyType.objects.filter(name__iexact=ENTRY_VILLA_NAME).update(booking_mode='room_types')


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0005_booking_mode_and_property_unit'),
    ]

    operations = [
        migrations.RunPython(set_entry_villa_whole_property, unset_entry_villa_whole_property),
    ]
