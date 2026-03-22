from django.contrib import admin
from .models import ContactMessage, Advertisement, SiteSetting, JobPosting

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

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ga4_tracking_id')
    
    # Ye ensure karega ki admin galti se multiple settings add na kar de
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)
    
@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'employment_type', 'is_active', 'created_at')
    list_filter = ('is_active', 'employment_type')
    list_editable = ('is_active',) # Admin bahar se hi tick/untick kar payega
    search_fields = ('title', 'location')