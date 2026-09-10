from django.contrib import admin
from .models import Booking, BookingGuest, Availability

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_reference', 'guest', 'property', 'check_in_date', 'status', 'payment_status']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['booking_reference', 'guest__email']
    readonly_fields = ['booking_reference', 'created_at', 'updated_at']

@admin.register(BookingGuest)
class BookingGuestAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'booking', 'is_primary_guest']

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ['room_type', 'date', 'status', 'available_count']
    list_filter = ['status', 'date']
