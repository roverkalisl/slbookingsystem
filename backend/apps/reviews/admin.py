from django.contrib import admin
from .models import Review, ReviewResponse

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['property', 'guest', 'overall_rating', 'is_published', 'created_at']
    list_filter = ['overall_rating', 'is_published', 'created_at']
    search_fields = ['property__name', 'guest__email']

@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    list_display = ['review', 'owner', 'created_at']
