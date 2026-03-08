from django.contrib import admin
from .models import ContactMessage, Advertisement

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('name', 'email', 'subject')

# --- NEW: Advertisement Admin Setup ---
@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    # Columns to show in the admin list view
    list_display = ('title', 'slot', 'ad_type', 'is_active', 'priority', 'created_at')
    
    # Add filters on the right sidebar
    list_filter = ('slot', 'ad_type', 'is_active', 'is_mobile_only')
    
    # Add a search bar
    search_fields = ('title', 'url')
    
    # Allow quick toggling of active status and priority without opening the item
    list_editable = ('is_active', 'priority')
    
    # Organize the form nicely when adding/editing an ad
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'slot', 'ad_type', 'is_active', 'priority', 'is_mobile_only')
        }),
        ('Brand Ad Details (Image + Link)', {
            'fields': ('image', 'url'),
            'description': 'Fill these if Ad Type is "Brand Collab". Leave Google Ad Code empty.'
        }),
        ('Google AdSense Details', {
            'fields': ('google_ad_code',),
            'description': 'Fill this if Ad Type is "Google AdSense". Leave Image and URL empty.'
        }),
    )