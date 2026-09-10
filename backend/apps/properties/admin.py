from django.contrib import admin
from .models import (
    PropertyType, Amenity, Destination, Property, PropertyPhoto, PropertyAmenity,
    RoomType, RoomTypePhoto, RoomTypeAmenity, Pricing, SeasonalRate
)

@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    search_fields = ['name']

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'is_published']
    search_fields = ['name', 'city']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'city', 'status', 'created_at']
    list_filter = ['status', 'city', 'created_at']
    search_fields = ['name', 'owner__email']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(PropertyPhoto)
class PropertyPhotoAdmin(admin.ModelAdmin):
    list_display = ['property', 'is_cover', 'display_order']

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ['property', 'name', 'max_adults', 'total_rooms', 'is_active']
    list_filter = ['property', 'is_active']

@admin.register(RoomTypePhoto)
class RoomTypePhotoAdmin(admin.ModelAdmin):
    list_display = ['room_type', 'is_cover', 'display_order']


@admin.register(Pricing)
class PricingAdmin(admin.ModelAdmin):
    list_display = ['room_type', 'base_price', 'weekend_price', 'currency']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SeasonalRate)
class SeasonalRateAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'start_date', 'end_date', 'price_per_night']
    list_filter = ['room_type', 'start_date', 'end_date']
    search_fields = ['name']
