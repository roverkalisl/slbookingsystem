from django.contrib import admin
from django.utils.timezone import now
from .models import (
    PropertyType, Amenity, Destination, Property, PropertyPhoto, PropertyAmenity,
    RoomType, RoomTypePhoto, RoomTypeAmenity, Pricing, SeasonalRate, PropertyContact
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
    list_display = ['name', 'owner', 'city', 'status', 'submitted_at', 'reviewed_at', 'created_at']
    list_filter = ['status', 'city', 'created_at', 'submitted_at']
    search_fields = ['name', 'owner__email', 'city']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'published_at', 'submitted_at', 'reviewed_at', 'reviewed_by']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'owner', 'property_type', 'short_description', 'description')
        }),
        ('Location', {
            'fields': ('address', 'city', 'district', 'province', 'postal_code', 'latitude', 'longitude', 'google_maps_url', 'nearby_attractions')
        }),
        ('Status & Approval', {
            'fields': ('status', 'submitted_at', 'reviewed_at', 'reviewed_by', 'rejection_reason')
        }),
        ('House Rules & Media', {
            'fields': ('house_rules', 'cover_photo_url')
        }),
        ('Ratings', {
            'fields': ('average_rating', 'total_reviews')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_property', 'reject_property', 'suspend_property', 'unsuspend_property', 'unpublish_property']

    def approve_property(self, request, queryset):
        """Approve properties"""
        count = 0
        for prop in queryset:
            if prop.status in ['pending_approval', 'rejected']:
                prop.status = 'approved'
                prop.reviewed_at = now()
                prop.reviewed_by = request.user
                prop.save()
                count += 1
        self.message_user(request, f'{count} properties approved.')
    approve_property.short_description = "✅ Approve selected properties"

    def reject_property(self, request, queryset):
        """Reject properties (requires reason via dialog)"""
        # This is a simplified version - in production, you'd use a custom form
        count = 0
        for prop in queryset:
            if prop.status in ['pending_approval']:
                prop.status = 'rejected'
                prop.reviewed_at = now()
                prop.reviewed_by = request.user
                prop.rejection_reason = "Rejected by admin"  # TODO: Add custom form for reason
                prop.save()
                count += 1
        self.message_user(request, f'{count} properties rejected.')
    reject_property.short_description = "❌ Reject selected properties"

    def suspend_property(self, request, queryset):
        """Suspend properties"""
        count = queryset.exclude(status='suspended').update(status='suspended')
        self.message_user(request, f'{count} properties suspended.')
    suspend_property.short_description = "🚫 Suspend selected properties"

    def unsuspend_property(self, request, queryset):
        """Unsuspend properties back to approved status"""
        count = queryset.filter(status='suspended').update(status='approved')
        self.message_user(request, f'{count} properties unsuspended.')
    unsuspend_property.short_description = "✓ Unsuspend selected properties"

    def unpublish_property(self, request, queryset):
        """Unpublish properties"""
        count = queryset.exclude(status='unpublished').update(status='unpublished')
        self.message_user(request, f'{count} properties unpublished.')
    unpublish_property.short_description = "📴 Unpublish selected properties"

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


@admin.register(PropertyContact)
class PropertyContactAdmin(admin.ModelAdmin):
    list_display = ['property', 'contact_person_name', 'contact_phone', 'whatsapp_number', 'email']
    search_fields = ['property__name', 'contact_person_name', 'contact_phone', 'whatsapp_number', 'email']
    readonly_fields = ['created_at', 'updated_at']
