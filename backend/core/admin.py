"""
core/admin.py — Site Control Panel Admin

Features:
  ✅ Contact message management with reply action + resolved tracking
  ✅ Advertisement management with active/inactive badges + priority editing
  ✅ Advertise Page singleton control
  ✅ Advertise Options with drag-sort order
  ✅ Site Settings singleton (GA4 tracking ID)
  ✅ Job Posting management with employment type badges
  ✅ Dashboard stats in changelist views
"""

from django.contrib import admin, messages
from django.conf import settings
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

from .models import (
    Advertisement,
    AdvertiseOption,
    AdvertisePage,
    ContactMessage,
    JobPosting,
    SiteSetting,
)


# ═══════════════════════════════════════════════════════════════════════════
#  CONTACT MESSAGE ADMIN
# ═══════════════════════════════════════════════════════════════════════════

class ContactResolvedFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('resolved',   'Resolved'),
            ('unresolved', 'Unresolved'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'resolved':
            return queryset.filter(is_resolved=True)
        if self.value() == 'unresolved':
            return queryset.filter(is_resolved=False)
        return queryset


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display  = ('name', 'email_display', 'subject_preview', 'status_badge', 'created_at')
    list_filter   = (ContactResolvedFilter, 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    date_hierarchy = 'created_at'
    ordering      = ('is_resolved', '-created_at')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')
    actions = ['mark_resolved', 'mark_unresolved']

    fieldsets = (
        ('Message Details', {
            'fields': ('name', 'email', 'subject', 'message', 'created_at'),
        }),
        ('Resolution Status', {
            'fields': ('is_resolved',),
        }),
    )

    @admin.display(description='Email')
    def email_display(self, obj):
        return format_html(
            '<a href="mailto:{}" style="color:#2563eb;">{}</a>',
            obj.email, obj.email,
        )

    @admin.display(description='Subject')
    def subject_preview(self, obj):
        return obj.subject[:55] + '…' if len(obj.subject) > 55 else obj.subject

    @admin.display(description='Status', ordering='is_resolved')
    def status_badge(self, obj):
        if obj.is_resolved:
            return format_html('<span style="color:#10b981;font-weight:bold;">Resolved</span>')
        return format_html('<span style="color:#ef4444;font-weight:bold;">Pending</span>')

    @admin.action(description='Mark selected as Resolved')
    def mark_resolved(self, request, queryset):
        count = queryset.update(is_resolved=True)
        self.message_user(request, f'{count} message(s) marked as resolved.')

    @admin.action(description='Mark selected as Unresolved')
    def mark_unresolved(self, request, queryset):
        count = queryset.update(is_resolved=False)
        self.message_user(request, f'{count} message(s) marked as unresolved.', level=messages.WARNING)


# ═══════════════════════════════════════════════════════════════════════════
#  ADVERTISEMENT ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display  = ('title', 'slot_badge', 'type_badge', 'priority', 'is_active', 'created_at')
    list_filter   = ('slot', 'ad_type', 'is_active', 'is_mobile_only', 'created_at')
    search_fields = ('title', 'url', 'google_ad_code')
    list_editable = ('is_active', 'priority')
    ordering      = ('-priority', '-created_at')
    date_hierarchy = 'created_at'
    actions = ['activate_ads', 'deactivate_ads']

    fieldsets = (
        ('Ad Setup', {
            'fields': ('title', 'slot', 'ad_type', 'is_active', 'priority', 'is_mobile_only'),
        }),
        ('Brand Ad Details', {
            'fields': ('image', 'url'),
        }),
        ('Google AdSense', {
            'fields': ('google_ad_code',),
        }),
    )

    @admin.display(description='Slot', ordering='slot')
    def slot_badge(self, obj):
        return format_html('<span style="font-weight:bold;">{}</span>', obj.get_slot_display())

    @admin.display(description='Type', ordering='ad_type')
    def type_badge(self, obj):
        if obj.ad_type == 'brand':
            return format_html('<span style="color:#d97706;font-weight:bold;">Brand</span>')
        return format_html('<span style="color:#059669;font-weight:bold;">AdSense</span>')

    @admin.action(description='Activate selected ads')
    def activate_ads(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} ad(s) activated.')

    @admin.action(description='Deactivate selected ads')
    def deactivate_ads(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} ad(s) deactivated.', level=messages.WARNING)


# ═══════════════════════════════════════════════════════════════════════════
#  ADVERTISE PAGE ADMIN (Singleton)
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(AdvertisePage)
class AdvertisePageAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Hero Section', {
            'fields': ('hero_title', 'hero_description'),
        }),
        ('Slots Section', {
            'fields': ('slots_section_title',),
        }),
        ('Inquiry Section', {
            'fields': ('inquiry_title', 'inquiry_description', 'submit_button_text', 'success_message'),
        }),
    )

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  ADVERTISE OPTION ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(AdvertiseOption)
class AdvertiseOptionAdmin(admin.ModelAdmin):
    list_display  = ('title', 'sort_order', 'is_active', 'show_on_page', 'show_in_inquiry_form', 'inquiry_value')
    list_filter   = ('is_active', 'show_on_page', 'show_in_inquiry_form')
    search_fields = ('title', 'description', 'inquiry_value')
    list_editable = ('sort_order', 'is_active', 'show_on_page', 'show_in_inquiry_form')
    ordering      = ('sort_order', 'id')


# ═══════════════════════════════════════════════════════════════════════════
#  SITE SETTINGS ADMIN (Singleton)
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'ga4_status')

    fieldsets = (
        ('Analytics', {
            'fields': ('ga4_tracking_id',),
        }),
    )

    @admin.display(description='GA4 Status')
    def ga4_status(self, obj):
        if obj.ga4_tracking_id:
            return format_html('<span style="color:#10b981;font-weight:bold;">Active</span>')
        return format_html('<span style="color:#d97706;font-weight:bold;">Not configured</span>')

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  JOB POSTING ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display  = ('title', 'location', 'employment_type_badge', 'is_active', 'created_at')
    list_filter   = ('is_active', 'employment_type', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'location', 'description')
    date_hierarchy = 'created_at'
    ordering      = ('-is_active', '-created_at')
    actions = ['open_jobs', 'close_jobs']

    fieldsets = (
        ('Job Details', {
            'fields': ('title', 'location', 'employment_type', 'description', 'is_active'),
        }),
    )

    @admin.display(description='Type', ordering='employment_type')
    def employment_type_badge(self, obj):
        TYPE_STYLES = {
            'full_time':   ('#1e3a8a', '#93c5fd', '⏰'),
            'part_time':   ('#4c1d95', '#c4b5fd', '🕐'),
            'contract':    ('#7f1d1d', '#fca5a5', '📄'),
            'internship':  ('#064e3b', '#6ee7b7', '🎓'),
            'freelance':   ('#78350f', '#fcd34d', '🎯'),
        }
        bg, color, emoji = TYPE_STYLES.get(obj.employment_type, ('#374151', '#9ca3af', '?'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 9px;border-radius:20px;font-size:10px;font-weight:700;">'
            '{} {}</span>',
            bg, color, emoji, obj.get_employment_type_display(),
        )

    @admin.display(description='Status', ordering='is_active')
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color:#10b981;font-weight:700;">🟢 Open</span>'
            )
        return format_html(
            '<span style="color:#6b7280;font-weight:600;">⚫ Closed</span>'
        )

    @admin.action(description='🟢 Open selected job postings')
    def activate_jobs(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'🟢 {count} job(s) opened.')

    @admin.action(description='⚫ Close selected job postings')
    def deactivate_jobs(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'⚫ {count} job(s) closed.', level=messages.WARNING)

    def changelist_view(self, request, extra_context=None):
        total  = JobPosting.objects.count()
        open_  = JobPosting.objects.filter(is_active=True).count()
        closed = total - open_
        messages.info(
            request,
            f'💼 Jobs — Total: {total}  |  🟢 Open: {open_}  |  ⚫ Closed: {closed}'
        )
        return super().changelist_view(request, extra_context=extra_context)
