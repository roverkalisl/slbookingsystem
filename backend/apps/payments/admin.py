from django.contrib import admin
from .models import Payment, Refund

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['booking', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['booking', 'amount', 'status', 'reason', 'created_at']
    list_filter = ['status', 'created_at']
