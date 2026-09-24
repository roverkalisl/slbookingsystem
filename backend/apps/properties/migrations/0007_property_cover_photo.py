"""
One cover photo per property.

Before adding the constraint, normalise existing data without deleting any
photo: where a property has several is_cover photos only the first (by
display order) keeps the flag; where it has photos but no cover, the first
photo becomes the cover. Property.cover_photo_url is then synced to the
cover's Cloudinary URL (or cleared when the property has no photos).
"""

from django.db import migrations, models


def normalise_cover_photos(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    PropertyPhoto = apps.get_model('properties', 'PropertyPhoto')

    for property_obj in Property.objects.all().iterator():
        photos = PropertyPhoto.objects.filter(property_id=property_obj.pk).order_by(
            '-is_cover', 'display_order', 'created_at'
        )
        cover = photos.first()
        if cover is None:
            if property_obj.cover_photo_url is not None:
                Property.objects.filter(pk=property_obj.pk).update(cover_photo_url=None)
            continue
        photos.exclude(pk=cover.pk).filter(is_cover=True).update(is_cover=False)
        if not cover.is_cover:
            PropertyPhoto.objects.filter(pk=cover.pk).update(is_cover=True)
        if property_obj.cover_photo_url != cover.cloudinary_url:
            Property.objects.filter(pk=property_obj.pk).update(cover_photo_url=cover.cloudinary_url)


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0006_entry_villa_whole_property'),
    ]

    operations = [
        migrations.RunPython(normalise_cover_photos, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='propertyphoto',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_cover', True)),
                fields=('property',),
                name='unique_cover_photo_per_property',
            ),
        ),
    ]
