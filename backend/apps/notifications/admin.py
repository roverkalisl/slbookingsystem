from django.contrib import admin
from .models import Notification, WhatsAppNotification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'channel', 'status', 'created_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['recipient__email', 'title']
    readonly_fields = ['created_at']


@admin.register(WhatsAppNotification)
class WhatsAppNotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient_phone', 'event_type', 'status', 'whatsapp_message_id', 'created_at', 'sent_at']
    list_filter = ['event_type', 'status', 'created_at']
    search_fields = ['recipient_phone', 'message_text', 'whatsapp_message_id']
    readonly_fields = ['created_at', 'whatsapp_message_id']

    fieldsets = (
        ('Recipient & Event', {
            'fields': ('recipient_phone', 'event_type')
        }),
        ('Related Objects', {
            'fields': ('booking', 'property')
        }),
        ('Message', {
            'fields': ('message_text',)
        }),
        ('Status', {
            'fields': ('status', 'whatsapp_message_id', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
