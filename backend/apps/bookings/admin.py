from django.contrib import admin
from .models import Booking, BookingGuest, Availability


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'guest', 'property', 'check_in_date', 'check_out_date', 'status', 'payment_status', 'total_price']
    list_filter = ['status', 'payment_status', 'created_at', 'property']
    search_fields = ['booking_reference', 'guest__email', 'property__name']
    readonly_fields = ['booking_reference', 'created_at', 'updated_at']
    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_reference', 'property', 'room_type', 'guest', 'status', 'payment_status')
        }),
        ('Dates', {
            'fields': ('check_in_date', 'check_out_date', 'number_of_nights')
        }),
        ('Guests', {
            'fields': ('number_of_adults', 'number_of_children', 'number_of_rooms')
        }),
        ('Pricing', {
            'fields': ('room_price', 'subtotal', 'discount', 'service_fee', 'tax', 'total_price')
        }),
        ('Notes', {
            'fields': ('special_requests',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(BookingGuest)
class BookingGuestAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'booking', 'is_primary_guest']
    list_filter = ['is_primary_guest', 'created_at']
    search_fields = ['first_name', 'last_name', 'email']


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ['room_type', 'date', 'status', 'available_count']
    list_filter = ['status', 'date', 'room_type']
    search_fields = ['room_type__name']
    readonly_fields = ['room_type', 'date', 'created_at', 'updated_at']

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of availability records"""
        return False
