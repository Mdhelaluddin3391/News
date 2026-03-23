from django.contrib import admin
from .models import ContactMessage, Advertisement, SiteSetting, JobPosting

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    date_hierarchy = 'created_at' # NAYA: Calendar filter top par
    actions = ['mark_as_resolved', 'mark_as_unresolved'] # NAYA: Bulk actions

    @admin.action(description='✅ Mark selected messages as Resolved')
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True)
        self.message_user(request, f"{updated} messages marked as resolved.")

    @admin.action(description='❌ Mark selected messages as Unresolved')
    def mark_as_unresolved(self, request, queryset):
        queryset.update(is_resolved=False)

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'slot', 'ad_type', 'is_active', 'priority', 'created_at')
    list_filter = ('slot', 'ad_type', 'is_active', 'is_mobile_only', 'created_at')
    search_fields = ('title', 'url', 'google_ad_code')
    list_editable = ('is_active', 'priority')
    date_hierarchy = 'created_at'
    actions = ['activate_ads', 'deactivate_ads']

    fieldsets = (
        ('Basic Info', {'fields': ('title', 'slot', 'ad_type', 'is_active', 'priority', 'is_mobile_only')}),
        ('Brand Ad Details', {'fields': ('image', 'url'), 'description': 'Only for Brand Collab.'}),
        ('Google AdSense', {'fields': ('google_ad_code',), 'description': 'Only for Google AdSense.'}),
    )

    @admin.action(description='🟢 Activate selected ads')
    def activate_ads(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='🔴 Deactivate selected ads')
    def deactivate_ads(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ga4_tracking_id')
    
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'employment_type', 'is_active', 'created_at')
    list_filter = ('is_active', 'employment_type', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'location', 'description')
    date_hierarchy = 'created_at'