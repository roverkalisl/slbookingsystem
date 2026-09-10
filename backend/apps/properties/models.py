"""
Property models for SL Booking.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils.text import slugify
from apps.core.models import User


class PropertyType(models.Model):
    """Property type configuration"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_types'
        ordering = ['name']

    def __str__(self):
        return self.name


class Amenity(models.Model):
    """Amenities that can be assigned to properties and rooms"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'amenities'
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class Destination(models.Model):
    """Destination pages for SEO"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    cover_image_url = models.URLField(blank=True, null=True)

    city = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)

    # SEO
    seo_title = models.CharField(max_length=255, blank=True, null=True)
    seo_description = models.CharField(max_length=500, blank=True, null=True)
    seo_keywords = models.CharField(max_length=500, blank=True, null=True)

    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'destinations'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return self.name


class Property(models.Model):
    """Main property model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('published', 'Published'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    property_type = models.ForeignKey(PropertyType, on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True, null=True)

    # Location
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, db_index=True)
    district = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    google_maps_url = models.URLField(blank=True, null=True)

    # Status
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending', db_index=True)

    # Media
    cover_photo_url = models.URLField(blank=True, null=True)

    # Ratings
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.IntegerField(default=0)

    # Amenities
    amenities = models.ManyToManyField(Amenity, through='PropertyAmenity', blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'properties'
        indexes = [
            models.Index(fields=['owner_id']),
            models.Index(fields=['city']),
            models.Index(fields=['status']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PropertyPhoto(models.Model):
    """Photos for properties"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='photos')
    cloudinary_url = models.URLField()
    cloudinary_public_id = models.CharField(max_length=255)
    caption = models.CharField(max_length=255, blank=True, null=True)
    display_order = models.IntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property_photos'
        indexes = [
            models.Index(fields=['property_id']),
            models.Index(fields=['display_order']),
        ]
        ordering = ['display_order']

    def __str__(self):
        return f"Photo for {self.property.name}"


class PropertyAmenity(models.Model):
    """Property-amenity relationship"""
    id = models.AutoField(primary_key=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)

    class Meta:
        db_table = 'property_amenities'
        unique_together = ('property', 'amenity')

    def __str__(self):
        return f"{self.property.name} - {self.amenity.name}"


class RoomType(models.Model):
    """Room types within a property"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='room_types')

    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)

    # Occupancy
    max_adults = models.IntegerField(default=2)
    max_children = models.IntegerField(default=0)
    total_occupancy = models.IntegerField(default=2)

    # Bed configuration
    bed_type = models.CharField(max_length=50, blank=True, null=True)
    number_of_beds = models.IntegerField(default=1)

    # Inventory
    total_rooms = models.IntegerField(default=1)

    # Physical
    room_size_sqm = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'room_types'
        indexes = [
            models.Index(fields=['property_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class RoomTypePhoto(models.Model):
    """Photos for room types"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='photos')
    cloudinary_url = models.URLField()
    cloudinary_public_id = models.CharField(max_length=255)
    display_order = models.IntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'room_type_photos'
        indexes = [
            models.Index(fields=['room_type_id']),
        ]
        ordering = ['display_order']

    def __str__(self):
        return f"Photo for {self.room_type.name}"


class RoomTypeAmenity(models.Model):
    """Room type-amenity relationship"""
    id = models.AutoField(primary_key=True)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)

    class Meta:
        db_table = 'room_type_amenities'
        unique_together = ('room_type', 'amenity')

    def __str__(self):
        return f"{self.room_type.name} - {self.amenity.name}"


class Pricing(models.Model):
    """Base pricing for room types"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_type = models.OneToOneField(RoomType, on_delete=models.CASCADE, related_name='pricing', unique=True)

    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    weekend_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    extra_guest_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    child_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    service_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('5.0'))
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.0'))

    currency = models.CharField(max_length=3, default='LKR')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pricing'
        indexes = [
            models.Index(fields=['room_type_id']),
        ]

    def __str__(self):
        return f"Pricing for {self.room_type.name}: {self.base_price} {self.currency}/night"


class SeasonalRate(models.Model):
    """Seasonal pricing overrides base pricing"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='seasonal_rates')

    name = models.CharField(max_length=100)  # "High Season", "Off Season", etc.
    price_per_night = models.DecimalField(max_digits=12, decimal_places=2)

    start_date = models.DateField()
    end_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seasonal_rates'
        indexes = [
            models.Index(fields=['room_type_id']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
