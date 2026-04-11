"""
interactions/admin.py — Full Moderation & Engagement Admin Panel

Features:
  ✅ Comment moderation with one-click approve/hide + bulk actions
  ✅ Comment report queue with priority sorting (unreviewed first)
  ✅ Newsletter management with total/active/unsubscribed stats
  ✅ Newsletter bulk email send action
  ✅ Poll management with live vote counts per option
  ✅ Push subscription management with user link
  ✅ Bookmark tracking (who saved what)
  ✅ CommentReport review workflow: Dismiss / Hide / Delete / Warn User
"""

from django.contrib import admin, messages
from django.conf import settings
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import timedelta

from core.tasks import send_async_email
from news.models import Article
from .models import (
    Bookmark, Comment, CommentReport,
    NewsletterSubscriber, Poll, PollOption, PushSubscription,
)


# ═══════════════════════════════════════════════════════════════════════════
#  BOOKMARK ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display  = ('user_email', 'article_title', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('user__email', 'user__name', 'article__title')
    date_hierarchy = 'created_at'
    autocomplete_fields = ['user', 'article']

    @admin.display(description='User', ordering='user__email')
    def user_email(self, obj):
        return format_html(
            '<span style="color:#93c5fd;">{}</span>', obj.user.email
        )

    @admin.display(description='Article', ordering='article__title')
    def article_title(self, obj):
        return obj.article.title[:60] + '…' if len(obj.article.title) > 60 else obj.article.title


# ═══════════════════════════════════════════════════════════════════════════
#  COMMENT ADMIN — Full Moderation Panel
# ═══════════════════════════════════════════════════════════════════════════

class CommentStatusFilter(admin.SimpleListFilter):
    title = '🗨️ Status'
    parameter_name = 'comment_status'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        active   = qs.filter(is_active=True).count()
        hidden   = qs.filter(is_active=False).count()
        reported = qs.filter(reports__isnull=False).distinct().count()
        return [
            ('active',   f'✅ Visible ({active})'),
            ('hidden',   f'🚫 Hidden ({hidden})'),
            ('reported', f'🚨 Has Reports ({reported})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_active=True)
        if self.value() == 'hidden':
            return queryset.filter(is_active=False)
        if self.value() == 'reported':
            return queryset.filter(reports__isnull=False).distinct()
        return queryset


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = (
        'user_display', 'article_display',
        'comment_preview', 'report_count',
        'status_badge', 'created_at',
    )
    list_display_links = ('comment_preview',)
    list_filter   = (CommentStatusFilter, 'created_at')
    search_fields = ('text', 'user__email', 'user__name', 'article__title')
    list_editable = ('is_active',) if False else ()  # We keep manual editable off — use actions
    date_hierarchy = 'created_at'
    actions       = ['approve_comments', 'hide_comments']
    readonly_fields = ('user', 'article', 'created_at', 'updated_at', 'report_count')

    fieldsets = (
        ('💬 Comment Details', {
            'fields': ('user', 'article', 'text', 'created_at', 'updated_at'),
        }),
        ('🛡️ Moderation', {
            'fields': ('is_active', 'report_count'),
        }),
    )

    @admin.display(description='👤 User', ordering='user__email')
    def user_display(self, obj):
        return format_html(
            '<span style="color:#93c5fd;font-weight:500;">{}</span>',
            obj.user.name or obj.user.email,
        )

    @admin.display(description='📰 Article')
    def article_display(self, obj):
        title = obj.article.title
        return title[:45] + '…' if len(title) > 45 else title

    @admin.display(description='Comment')
    def comment_preview(self, obj):
        return obj.text[:70] + '…' if len(obj.text) > 70 else obj.text

    @admin.display(description='🚨 Reports')
    def report_count(self, obj):
        count = obj.reports.count()
        if count == 0:
            return format_html('<span style="color:#4b5563;">—</span>')
        color = '#ef4444' if count >= 3 else '#f59e0b'
        return format_html(
            '<span style="color:{};font-weight:700;font-size:13px;">⚠️ {}</span>',
            color, count,
        )

    @admin.display(description='Status', ordering='is_active')
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#064e3b;color:#6ee7b7;padding:2px 9px;'
                'border-radius:20px;font-size:10px;font-weight:700;">✅ VISIBLE</span>'
            )
        return format_html(
            '<span style="background:#7f1d1d;color:#fca5a5;padding:2px 9px;'
            'border-radius:20px;font-size:10px;font-weight:700;">🚫 HIDDEN</span>'
        )

    @admin.action(description='✅ Approve (Show) selected comments')
    def approve_comments(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'✅ {count} comment(s) approved and made visible.')

    @admin.action(description='🚫 Hide (Moderate) selected comments')
    def hide_comments(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'🚫 {count} comment(s) hidden from public view.', level=messages.WARNING)

    def changelist_view(self, request, extra_context=None):
        total    = Comment.objects.count()
        active   = Comment.objects.filter(is_active=True).count()
        hidden   = Comment.objects.filter(is_active=False).count()
        reported = Comment.objects.filter(reports__isnull=False).distinct().count()
        messages.info(
            request,
            f'💬 Total: {total}  |  ✅ Visible: {active}  |  🚫 Hidden: {hidden}  |  🚨 Reported: {reported}'
        )
        return super().changelist_view(request, extra_context=extra_context)


# ═══════════════════════════════════════════════════════════════════════════
#  COMMENT REPORT ADMIN — Priority Queue
# ═══════════════════════════════════════════════════════════════════════════

class ReportPriorityFilter(admin.SimpleListFilter):
    title = '📋 Review Status'
    parameter_name = 'review_status'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        pending  = qs.filter(is_reviewed=False).count()
        reviewed = qs.filter(is_reviewed=True).count()
        return [
            ('pending',  f'🔴 Pending Review ({pending})'),
            ('reviewed', f'✅ Reviewed ({reviewed})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(is_reviewed=False)
        if self.value() == 'reviewed':
            return queryset.filter(is_reviewed=True)
        return queryset


@admin.register(CommentReport)
class CommentReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'comment_preview_short', 'comment_author',
        'reported_by_display', 'reason_badge', 'review_status', 'admin_action_display', 'created_at',
    )
    list_display_links = ('id', 'comment_preview_short')
    list_filter = (
        ReportPriorityFilter, 'reason', 'admin_action', 'created_at',
    )
    search_fields = (
        'comment__text', 'comment__user__email',
        'reported_by__email', 'description',
    )
    ordering = ('is_reviewed', '-created_at')  # Unreviewed first
    date_hierarchy = 'created_at'
    readonly_fields = (
        'comment', 'reported_by', 'comment_preview', 'comment_author', 'created_at',
    )

    fieldsets = (
        ('🚨 Report Details', {
            'fields': ('comment', 'comment_author', 'comment_preview', 'reported_by', 'reason', 'description', 'created_at'),
        }),
        ('⚖️ Admin Review & Action', {
            'fields': ('is_reviewed', 'admin_action', 'admin_notes'),
            'description': 'Select action and save to apply moderation.',
        }),
    )

    actions = [
        'mark_reviewed',
        'dismiss_reports_action',
        'hide_comment_action',
        'remove_comment_action',
        'warn_user_action',
    ]

    # ── Custom columns ─────────────────────────────────────────────────────

    @admin.display(description='Comment')
    def comment_preview_short(self, obj):
        text = obj.comment.text
        return text[:55] + '…' if len(text) > 55 else text

    @admin.display(description='Full Comment')
    def comment_preview(self, obj):
        return obj.comment.text

    @admin.display(description='Author', ordering='comment__user__email')
    def comment_author(self, obj):
        return format_html(
            '<span style="color:#93c5fd;">{}</span>',
            obj.comment.user.email,
        )

    @admin.display(description='Reported By')
    def reported_by_display(self, obj):
        return format_html(
            '<span style="color:#fcd34d;">{}</span>',
            obj.reported_by.email,
        )

    @admin.display(description='Reason', ordering='reason')
    def reason_badge(self, obj):
        COLORS = {
            'spam':          ('#92400e', '#fcd34d'),
            'offensive':     ('#7f1d1d', '#fca5a5'),
            'inappropriate': ('#4c1d95', '#c4b5fd'),
            'harassment':    ('#7f1d1d', '#f87171'),
            'false_info':    ('#1e3a8a', '#93c5fd'),
            'other':         ('#374151', '#9ca3af'),
        }
        bg, color = COLORS.get(obj.reason, ('#374151', '#9ca3af'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;">{}</span>',
            bg, color, obj.get_reason_display().upper(),
        )

    @admin.display(description='Status', ordering='is_reviewed')
    def review_status(self, obj):
        if obj.is_reviewed:
            return format_html('<span style="color:#10b981;font-weight:700;">✅ Done</span>')
        return format_html('<span style="color:#ef4444;font-weight:700;animation:none;">🔴 Pending</span>')

    @admin.display(description='Action Taken', ordering='admin_action')
    def admin_action_display(self, obj):
        ACTION_STYLES = {
            'none':      ('—', '#6b7280'),
            'hidden':    ('🚫 Hidden', '#f59e0b'),
            'deleted':   ('🗑️ Deleted', '#ef4444'),
            'warn_user': ('⚠️ Warned', '#f97316'),
        }
        label, color = ACTION_STYLES.get(obj.admin_action, ('?', '#6b7280'))
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, label)

    # ── Helpers ─────────────────────────────────────────────────────────────────
    def _mark_related(self, report, action, notes):
        CommentReport.objects.filter(comment=report.comment).update(
            is_reviewed=True, admin_action=action, admin_notes=notes
        )

    # ── Actions ────────────────────────────────────────────────────────────

    @admin.action(description='✅ Mark as Reviewed (No Action)')
    def mark_reviewed(self, request, queryset):
        count = queryset.update(is_reviewed=True)
        self.message_user(request, f'✅ {count} report(s) marked as reviewed.')

    @admin.action(description='🟢 Dismiss — Report was invalid')
    def dismiss_reports_action(self, request, queryset):
        queryset.update(is_reviewed=True, admin_action='none')
        self.message_user(request, f'🟢 {queryset.count()} reports dismissed.')

    @admin.action(description='🚫 Hide Comment from public view')
    def hide_comment_action(self, request, queryset):
        for report in queryset:
            report.comment.is_active = False
            report.comment.save(update_fields=['is_active'])
            self._mark_related(report, 'hidden', 'Hidden by admin via report interface.')
        self.message_user(request, f'🚫 {queryset.count()} comment(s) hidden.', level=messages.WARNING)

    @admin.action(description='🗑️ Remove Comment + Mark Actioned')
    def remove_comment_action(self, request, queryset):
        for report in queryset:
            report.comment.is_active = False
            report.comment.save(update_fields=['is_active'])
            self._mark_related(report, 'deleted', 'Removed from public view by admin.')
        self.message_user(request, f'🗑️ {queryset.count()} comment(s) removed.', level=messages.WARNING)

    @admin.action(description='⚠️ Flag User for Warning')
    def warn_user_action(self, request, queryset):
        for report in queryset:
            self._mark_related(report, 'warn_user', 'Author flagged for moderator warning.')
        self.message_user(request, f'⚠️ {queryset.count()} user(s) flagged for warning.')

    def save_model(self, request, obj, form, change):
        if obj.admin_action in ('hidden', 'deleted'):
            obj.comment.is_active = False
            obj.comment.save(update_fields=['is_active'])
        if obj.admin_action != 'none':
            obj.is_reviewed = True
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        pending = CommentReport.objects.filter(is_reviewed=False).count()
        if pending > 0:
            messages.warning(
                request,
                f'🚨 {pending} report(s) are PENDING review! Filter: 🔴 Pending Review to see them.'
            )
        return super().changelist_view(request, extra_context=extra_context)


# ═══════════════════════════════════════════════════════════════════════════
#  NEWSLETTER ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display  = ('email', 'status_badge', 'token_status', 'created_at')
    list_filter   = ('is_active', 'created_at')
    search_fields = ('email',)
    date_hierarchy = 'created_at'
    actions = [
        'activate_subscribers', 'deactivate_subscribers',
        'send_latest_news_email',
    ]
    readonly_fields = ('unsubscribe_token', 'unsubscribe_token_used_at')

    fieldsets = (
        ('📧 Subscriber Info', {
            'fields': ('email', 'is_active'),
        }),
        ('🔐 Unsubscribe Token', {
            'fields': ('unsubscribe_token', 'unsubscribe_token_used_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Status', ordering='is_active')
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#064e3b;color:#6ee7b7;padding:2px 9px;'
                'border-radius:20px;font-size:10px;font-weight:700;">✅ SUBSCRIBED</span>'
            )
        return format_html(
            '<span style="background:#374151;color:#9ca3af;padding:2px 9px;'
            'border-radius:20px;font-size:10px;font-weight:700;">🔕 UNSUBSCRIBED</span>'
        )

    @admin.display(description='Token')
    def token_status(self, obj):
        if obj.unsubscribe_token_used_at:
            return format_html(
                '<span style="color:#6b7280;font-size:11px;">Used {}</span>',
                obj.unsubscribe_token_used_at.strftime('%b %d'),
            )
        return format_html('<span style="color:#4b5563;font-size:11px;">—</span>')

    @admin.action(description='🟢 Activate selected subscribers')
    def activate_subscribers(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'🟢 {count} subscriber(s) activated.')

    @admin.action(description='🔕 Deactivate selected subscribers')
    def deactivate_subscribers(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'🔕 {count} subscriber(s) deactivated.', level=messages.WARNING)

    @admin.action(description='📧 Send Latest News to Selected Subscribers')
    def send_latest_news_email(self, request, queryset):
        active = queryset.filter(is_active=True)
        if not active.exists():
            self.message_user(request, '❌ No active subscribers in selection.', level=messages.ERROR)
            return

        latest = Article.objects.filter(status='published').order_by('-published_at')[:5]
        if not latest.exists():
            self.message_user(request, '❌ No published articles to send.', level=messages.ERROR)
            return

        subject = '📰 Latest Stories from Ferox Times'
        message_lines = ['Hello!\n\nHere are the latest top stories:\n']
        html_parts = [
            '<html><body style="font-family:Arial,sans-serif;background:#f8f9fa;padding:20px;">',
            '<div style="max-width:600px;margin:auto;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #e2e8f0;">',
            '<div style="background:#d32f2f;padding:20px;text-align:center;">',
            '<h1 style="color:#fff;margin:0;font-size:22px;">📰 Ferox Times</h1></div>',
            '<div style="padding:24px;">',
        ]

        base_url = settings.FRONTEND_URL
        for article in latest:
            url = f'{base_url}/article/{article.slug}'
            message_lines.append(f'➡️ {article.title}\n   {url}\n')
            html_parts.append(
                f'<div style="margin-bottom:20px;padding-bottom:20px;border-bottom:1px solid #e2e8f0;">'
                f'<h3 style="margin:0 0 8px 0;color:#1a365d;">{article.title}</h3>'
                f'<p style="color:#555;margin:0 0 8px 0;">{article.description[:120] if article.description else ""}...</p>'
                f'<a href="{url}" style="background:#d32f2f;color:#fff;padding:8px 16px;border-radius:4px;'
                f'text-decoration:none;font-size:13px;font-weight:bold;">Read Story →</a></div>'
            )

        html_parts += [
            '</div>',
            f'<div style="background:#f1f5f9;padding:14px;text-align:center;font-size:12px;color:#64748b;">',
            f'<a href="{base_url}/unsubscribe" style="color:#d32f2f;">Unsubscribe</a></div>',
            '</div></body></html>',
        ]

        recipients = list(active.values_list('email', flat=True))
        try:
            send_async_email.delay(subject, '\n'.join(message_lines), recipients, ''.join(html_parts))
            self.message_user(
                request,
                f'📧 Newsletter queued for {len(recipients)} subscriber(s)!'
            )
        except Exception as exc:
            self.message_user(request, f'❌ Email queue error: {exc}', level=messages.ERROR)

    def changelist_view(self, request, extra_context=None):
        total   = NewsletterSubscriber.objects.count()
        active  = NewsletterSubscriber.objects.filter(is_active=True).count()
        unsub   = total - active
        messages.info(
            request,
            f'📧 Newsletter Stats — Total: {total}  |  ✅ Active: {active}  |  🔕 Unsubscribed: {unsub}'
        )
        return super().changelist_view(request, extra_context=extra_context)


# ═══════════════════════════════════════════════════════════════════════════
#  POLL ADMIN — With Vote Counts
# ═══════════════════════════════════════════════════════════════════════════

class PollOptionInline(admin.TabularInline):
    model   = PollOption
    extra   = 2
    fields  = ('text', 'votes')
    readonly_fields = ('votes',)
    can_delete = True


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display  = ('question', 'total_votes', 'status_badge', 'created_at')
    list_filter   = ('is_active', 'created_at')
    search_fields = ('question', 'description')
    inlines       = [PollOptionInline]
    actions       = ['activate_poll', 'deactivate_poll']

    fieldsets = (
        ('📊 Poll Info', {
            'fields': ('question', 'description', 'is_active'),
            'description': 'Only ONE poll can be active at a time. Activating this will be used on the frontend.',
        }),
    )

    @admin.display(description='Total Votes')
    def total_votes(self, obj):
        total = sum(option.votes for option in obj.options.all())
        if total == 0:
            return format_html('<span style="color:#6b7280;">0 votes</span>')
        return format_html('<span style="color:#10b981;font-weight:700;">🗳️ {}</span>', total)

    @admin.display(description='Status', ordering='is_active')
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#064e3b;color:#6ee7b7;padding:2px 9px;'
                'border-radius:20px;font-size:10px;font-weight:700;">🟢 ACTIVE</span>'
            )
        return format_html(
            '<span style="background:#374151;color:#9ca3af;padding:2px 9px;'
            'border-radius:20px;font-size:10px;font-weight:700;">⚫ INACTIVE</span>'
        )

    @admin.action(description='🟢 Activate selected poll (deactivates others)')
    def activate_poll(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, '❌ Only one poll can be activated at a time.', level=messages.ERROR)
            return
        Poll.objects.update(is_active=False)
        queryset.update(is_active=True)
        self.message_user(request, '🟢 Poll activated! All other polls deactivated.')

    @admin.action(description='⚫ Deactivate selected poll')
    def deactivate_poll(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'⚫ {count} poll(s) deactivated.', level=messages.WARNING)


# ═══════════════════════════════════════════════════════════════════════════
#  PUSH SUBSCRIPTION ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display  = ('id', 'endpoint_short', 'user_display', 'created_at')
    search_fields = ('endpoint', 'user__email', 'user__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('endpoint', 'auth', 'p256dh', 'created_at')
    actions = ['delete_invalid_subscriptions']

    fieldsets = (
        ('📡 Subscription Details', {
            'fields': ('endpoint', 'user'),
        }),
        ('🔐 Encryption Keys (Read Only)', {
            'fields': ('auth', 'p256dh'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Endpoint')
    def endpoint_short(self, obj):
        return obj.endpoint[:60] + '…' if len(obj.endpoint) > 60 else obj.endpoint

    @admin.display(description='User', ordering='user__email')
    def user_display(self, obj):
        if obj.user:
            return format_html(
                '<span style="color:#93c5fd;">{}</span>', obj.user.email
            )
        return format_html('<span style="color:#6b7280;">Anonymous</span>')

    @admin.action(description='🗑️ Delete selected (expired/invalid) subscriptions')
    def delete_invalid_subscriptions(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f'🗑️ {count} push subscription(s) deleted.',
            level=messages.WARNING,
        )

    def changelist_view(self, request, extra_context=None):
        total    = PushSubscription.objects.count()
        with_user = PushSubscription.objects.filter(user__isnull=False).count()
        anon     = total - with_user
        messages.info(
            request,
            f'🔔 Push Subscriptions — Total: {total}  |  👤 Linked to User: {with_user}  |  🕵️ Anonymous: {anon}'
        )
        return super().changelist_view(request, extra_context=extra_context)
