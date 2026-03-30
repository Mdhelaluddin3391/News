from django.contrib import admin

from .models import (
    Advertisement,
    AdvertiseOption,
    AdvertisePage,
    ContactMessage,
    JobPosting,
    SiteSetting,
)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at", "is_resolved")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("name", "email", "subject", "message")
    date_hierarchy = "created_at"
    actions = ["mark_as_resolved", "mark_as_unresolved"]

    @admin.action(description="Mark selected messages as resolved")
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True)
        self.message_user(request, f"{updated} messages marked as resolved.")

    @admin.action(description="Mark selected messages as unresolved")
    def mark_as_unresolved(self, request, queryset):
        queryset.update(is_resolved=False)


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ("title", "slot", "ad_type", "is_active", "priority", "created_at")
    list_filter = ("slot", "ad_type", "is_active", "is_mobile_only", "created_at")
    search_fields = ("title", "url", "google_ad_code")
    list_editable = ("is_active", "priority")
    date_hierarchy = "created_at"
    actions = ["activate_ads", "deactivate_ads"]

    fieldsets = (
        ("Basic Info", {"fields": ("title", "slot", "ad_type", "is_active", "priority", "is_mobile_only")}),
        ("Brand Ad Details", {"fields": ("image", "url"), "description": "Only for Brand Collab."}),
        ("Google AdSense", {"fields": ("google_ad_code",), "description": "Only for Google AdSense."}),
    )

    @admin.action(description="Activate selected ads")
    def activate_ads(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected ads")
    def deactivate_ads(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(AdvertisePage)
class AdvertisePageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "hero_title", "submit_button_text")

    fieldsets = (
        ("Hero", {"fields": ("hero_title", "hero_description")}),
        ("Slots Section", {"fields": ("slots_section_title",)}),
        ("Inquiry Section", {"fields": ("inquiry_title", "inquiry_description", "submit_button_text", "success_message")}),
    )

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(AdvertiseOption)
class AdvertiseOptionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "inquiry_value",
        "sort_order",
        "is_active",
        "show_on_page",
        "show_in_inquiry_form",
    )
    list_filter = ("is_active", "show_on_page", "show_in_inquiry_form")
    search_fields = ("title", "inquiry_value", "description")
    list_editable = ("sort_order", "is_active", "show_on_page", "show_in_inquiry_form")
    ordering = ("sort_order", "id")


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("__str__", "ga4_tracking_id")

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "employment_type", "is_active", "created_at")
    list_filter = ("is_active", "employment_type", "created_at")
    list_editable = ("is_active",)
    search_fields = ("title", "location", "description")
    date_hierarchy = "created_at"
