from django.contrib import admin
from django.utils.html import format_html
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


def photo_preview(photo, height=80):
    """Thumbnail of a stored Cloudinary URL for the admin."""
    if not photo or not photo.cloudinary_url:
        return '-'
    return format_html('<img src="{}" style="height:{}px;border-radius:4px" />', photo.cloudinary_url, height)


class PropertyPhotoInline(admin.TabularInline):
    """Property photos with the cover clearly marked. The cover is changed with
    the "Set as cover" action on Property photos (keeps exactly one cover)."""
    model = PropertyPhoto
    extra = 0
    fields = ['preview', 'is_cover', 'display_order', 'caption', 'cloudinary_url']
    readonly_fields = ['preview', 'is_cover', 'cloudinary_url']
    ordering = ['-is_cover', 'display_order', 'created_at']

    @admin.display(description='Photo')
    def preview(self, obj):
        return photo_preview(obj)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'city', 'status', 'submitted_at', 'reviewed_at', 'created_at']
    list_filter = ['status', 'city', 'created_at', 'submitted_at']
    search_fields = ['name', 'owner__email', 'city']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'published_at', 'submitted_at', 'reviewed_at', 'reviewed_by',
                       'cover_photo_url', 'cover_photo_preview']
    inlines = [PropertyPhotoInline]

    @admin.display(description='Cover photo')
    def cover_photo_preview(self, obj):
        return photo_preview(obj.photos.filter(is_cover=True).first(), height=160)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Photos may have been added/deleted in the inline - keep exactly one cover.
        form.instance.ensure_cover_photo()

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
            'fields': ('house_rules', 'cover_photo_preview', 'cover_photo_url')
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
    list_display = ['property', 'preview', 'is_cover', 'display_order']
    list_filter = ['is_cover']
    search_fields = ['property__name']
    readonly_fields = ['preview', 'is_cover']
    actions = ['set_as_cover']

    @admin.display(description='Photo')
    def preview(self, obj):
        return photo_preview(obj)

    @admin.action(description='⭐ Set as cover (one per property)')
    def set_as_cover(self, request, queryset):
        # One cover per property: if several photos of a property are selected, the last one wins.
        count = 0
        for photo in queryset.select_related('property'):
            photo.property.set_cover_photo(photo)
            count += 1
        self.message_user(request, f'{count} cover photo(s) set.')

    def delete_model(self, request, obj):
        property_obj = obj.property
        super().delete_model(request, obj)
        property_obj.ensure_cover_photo()

    def delete_queryset(self, request, queryset):
        properties = {photo.property for photo in queryset.select_related('property')}
        super().delete_queryset(request, queryset)
        for property_obj in properties:
            property_obj.ensure_cover_photo()

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
