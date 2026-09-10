from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'channel', 'status', 'created_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['recipient__email', 'title']
