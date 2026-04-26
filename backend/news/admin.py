"""
news/admin.py — Ferox Times Industry-Grade Newsroom Admin Panel

Features:
  ✅ Category Admin — article count badge, slug autopop
  ✅ Tag Admin      — article count badge, slug autopop
  ✅ Author Admin   — article count, published count, social links, avatar preview
  ✅ LiveUpdate Admin — standalone register with article link
  ✅ Article Admin  — Premium list with:
       • Coloured status badge (Published / Draft)
       • AI import badge with source tooltip
       • Word count + estimated read time
       • Thumbnail image preview
       • Views badge
       • All special flags visible inline
       • Frontend link in list
  ✅ Bulk Actions:
       • Publish / Move to Draft
       • Regenerate slug
       • Run AI Import (GNews → Groq → Draft)
       • Force Trending / Featured / Remove flags
       • Post to Telegram
       • Export selected to CSV
  ✅ Role-based field access (Admin > Editor > Reporter/Author)
  ✅ Dashboard message: pending AI drafts warning
"""

import csv
import os
from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, strip_tags
from django.utils.text import slugify
from django.utils.timezone import now as timezone_now

from .models import Article, Author, Category, LiveUpdate, Tag


# ═══════════════════════════════════════════════════════════════════════════
#  HELPER UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _word_count(html_content: str) -> int:
    """Returns approximate word count from HTML article content."""
    if not html_content:
        return 0
    return len(strip_tags(html_content).split())


def _read_time(words: int) -> str:
    """Returns estimated read time string (assumes 200 WPM)."""
    mins = max(1, round(words / 200))
    return f"{mins} min"


# ═══════════════════════════════════════════════════════════════════════════
#  CUSTOM LIST FILTERS
# ═══════════════════════════════════════════════════════════════════════════

class StatusFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'article_status'

    def lookups(self, request, model_admin):
        draft_count = Article.objects.filter(status='draft').count()
        pub_count   = Article.objects.filter(status='published').count()
        return [
            ('draft',     f'Draft ({draft_count})'),
            ('published', f'Published ({pub_count})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'draft':
            return queryset.filter(status='draft')
        if self.value() == 'published':
            return queryset.filter(status='published')
        return queryset


class ImportTypeFilter(admin.SimpleListFilter):
    title = 'Article Type'
    parameter_name = 'import_type'

    def lookups(self, request, model_admin):
        ai_count     = Article.objects.filter(is_imported=True).count()
        manual_count = Article.objects.filter(is_imported=False).count()
        return [
            ('imported', f'🤖 AI Imported ({ai_count})'),
            ('manual',   f'✍️ Manual ({manual_count})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'imported':
            return queryset.filter(is_imported=True)
        if self.value() == 'manual':
            return queryset.filter(is_imported=False)
        return queryset


class PublishDateFilter(admin.SimpleListFilter):
    title = 'Published Date'
    parameter_name = 'pub_date'

    def lookups(self, request, model_admin):
        return [
            ('today',      '📅 Today'),
            ('yesterday',  '◀️ Yesterday'),
            ('this_week',  '🗓️ This Week'),
            ('last_7',     '📆 Last 7 Days'),
            ('this_month', '📋 This Month'),
            ('last_30',    '🗂️ Last 30 Days'),
            ('older',      '🗃️ Older'),
        ]

    def queryset(self, request, queryset):
        now   = timezone.now()
        today = now.date()
        if self.value() == 'today':
            return queryset.filter(published_at__date=today)
        if self.value() == 'yesterday':
            return queryset.filter(published_at__date=today - timedelta(days=1))
        if self.value() == 'this_week':
            return queryset.filter(published_at__date__gte=today - timedelta(days=today.weekday()))
        if self.value() == 'last_7':
            return queryset.filter(published_at__gte=now - timedelta(days=7))
        if self.value() == 'this_month':
            return queryset.filter(published_at__year=today.year, published_at__month=today.month)
        if self.value() == 'last_30':
            return queryset.filter(published_at__gte=now - timedelta(days=30))
        if self.value() == 'older':
            return queryset.filter(published_at__lt=now - timedelta(days=30))
        return queryset


class FlagsFilter(admin.SimpleListFilter):
    title = 'Special Flags'
    parameter_name = 'flags'

    def lookups(self, request, model_admin):
        return [
            ('breaking',     '🔴 Breaking News'),
            ('trending',     '🔥 Trending'),
            ('featured',     '⭐ Featured'),
            ('editors_pick', '✏️ Editor\'s Pick'),
            ('top_story',    '📌 Top Story'),
            ('live',         '🟢 Live Blog'),
            ('web_story',    '📖 Web Story'),
        ]

    def queryset(self, request, queryset):
        mapping = {
            'breaking':     {'is_breaking': True},
            'trending':     {'is_trending': True},
            'featured':     {'is_featured': True},
            'editors_pick': {'is_editors_pick': True},
            'top_story':    {'is_top_story': True},
            'live':         {'is_live': True},
            'web_story':    {'is_web_story': True},
        }
        if self.value() in mapping:
            return queryset.filter(**mapping[self.value()])
        return queryset


class HasImageFilter(admin.SimpleListFilter):
    title = 'Featured Image'
    parameter_name = 'has_image'

    def lookups(self, request, model_admin):
        return [
            ('yes', '🖼️ Has Image'),
            ('no',  '⬜ No Image'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(featured_image='').exclude(featured_image__isnull=True)
        if self.value() == 'no':
            return queryset.filter(Q(featured_image='') | Q(featured_image__isnull=True))
        return queryset


class SocialPostFilter(admin.SimpleListFilter):
    title = 'Social Media'
    parameter_name = 'social'

    def lookups(self, request, model_admin):
        return [
            ('pending_fb',  '📘 Facebook Pending'),
            ('pending_tw',  '🐦 Twitter Pending'),
            ('pending_tg',  '✈️ Telegram Pending'),
            ('push_sent',   '🔔 Push Sent'),
            ('push_unsent', '🔕 Push Not Sent'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'pending_fb':
            return queryset.filter(post_to_facebook=True)
        if self.value() == 'pending_tw':
            return queryset.filter(post_to_twitter=True)
        if self.value() == 'pending_tg':
            return queryset.filter(post_to_telegram=True)
        if self.value() == 'push_sent':
            return queryset.filter(push_sent=True)
        if self.value() == 'push_unsent':
            return queryset.filter(push_sent=False, status='published')
        return queryset


class ActivistDraftFilter(admin.SimpleListFilter):
    title = 'Contributor Drafts'
    parameter_name = 'activist_drafts'

    def lookups(self, request, model_admin):
        return [
            ('pending_review', '⏳ Pending Review'),
            ('published',      '✅ Published by Contributors'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'pending_review':
            return queryset.filter(status='draft', author__user__role='author')
        if self.value() == 'published':
            return queryset.filter(status='published', author__user__role='author')
        return queryset


# ═══════════════════════════════════════════════════════════════════════════
#  ARTICLE ADMIN FORM
# ═══════════════════════════════════════════════════════════════════════════

class ArticleAdminForm(forms.ModelForm):
    tags_input = forms.CharField(
        max_length=500,
        required=False,
        label='Tags',
        help_text=(
            'Enter comma-separated tags. e.g: Sports, Cricket, Live News. '
            'New tags will be auto-created; existing tags will be matched by slug.'
        ),
        widget=forms.TextInput(attrs={'placeholder': 'Technology, World, Breaking News, …'}),
    )

    class Meta:
        model = Article
        exclude = ('tags',)

    def __init__(self, *args, **kwargs):
        self._request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(
                tag.name for tag in self.instance.tags.all()
            )

    def clean_is_breaking(self):
        value   = self.cleaned_data.get('is_breaking', False)
        request = self._request
        if value and request:
            user     = request.user
            is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
            if not is_admin:
                raise forms.ValidationError(
                    "⛔ Only Admins can set the Breaking News flag. "
                    "Editors and Reporters do not have this permission."
                )
        return value


# ═══════════════════════════════════════════════════════════════════════════
#  INLINES
# ═══════════════════════════════════════════════════════════════════════════

class LiveUpdateInline(admin.TabularInline):
    model      = LiveUpdate
    extra      = 1
    fields     = ('timestamp', 'title', 'content')
    ordering   = ('-timestamp',)


# ═══════════════════════════════════════════════════════════════════════════
#  CATEGORY ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ('name', 'slug', 'article_count_badge', 'published_count_badge', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields       = ('name',)
    ordering            = ('name',)
    show_full_result_count = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _total_articles     = Count('articles', distinct=True),
            _published_articles = Count(
                'articles',
                filter=Q(articles__status='published'),
                distinct=True,
            ),
        )

    @admin.display(description='Total Articles', ordering='_total_articles')
    def article_count_badge(self, obj):
        count = getattr(obj, '_total_articles', 0)
        if count == 0:
            return format_html('<span style="color:#6b7280;">0</span>')
        return format_html(
            '<span style="background:#1e3a5f;color:#60a5fa;'
            'padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;">{}</span>',
            count,
        )

    @admin.display(description='Published', ordering='_published_articles')
    def published_count_badge(self, obj):
        count = getattr(obj, '_published_articles', 0)
        if count == 0:
            return format_html('<span style="color:#6b7280;">0</span>')
        return format_html(
            '<span style="background:#064e3b;color:#6ee7b7;'
            'padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;">{}</span>',
            count,
        )


# ═══════════════════════════════════════════════════════════════════════════
#  TAG ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display        = ('name', 'slug', 'article_count_badge', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields       = ('name',)
    ordering            = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _article_count=Count('article', distinct=True)
        )

    @admin.display(description='Articles', ordering='_article_count')
    def article_count_badge(self, obj):
        count = getattr(obj, '_article_count', 0)
        if count == 0:
            return format_html('<span style="color:#6b7280;">0</span>')
        return format_html(
            '<span style="background:#1e3a5f;color:#93c5fd;'
            'padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;">{}</span>',
            count,
        )


# ═══════════════════════════════════════════════════════════════════════════
#  AUTHOR ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display        = (
        'user_email', 'role',
        'article_count_badge', 'published_count_badge',
        'social_links', 'created_at',
    )
    search_fields       = ('user__name', 'user__email', 'role')
    autocomplete_fields = ['user']
    ordering            = ('-created_at',)
    readonly_fields     = ('slug',)

    fieldsets = (
        ('Profile', {
            'fields': ('user', 'role', 'slug'),
        }),
        ('Social Links', {
            'fields': ('twitter_url', 'linkedin_url'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _total     = Count('articles', distinct=True),
            _published = Count(
                'articles',
                filter=Q(articles__status='published'),
                distinct=True,
            ),
        )

    @admin.display(description='Author', ordering='user__email')
    def user_email(self, obj):
        return format_html(
            '<strong style="color:#93c5fd;">{}</strong><br>'
            '<span style="color:#64748b;font-size:11px;">{}</span>',
            obj.user.name or '—',
            obj.user.email,
        )

    @admin.display(description='Total', ordering='_total')
    def article_count_badge(self, obj):
        count = getattr(obj, '_total', 0)
        color = '#60a5fa' if count > 0 else '#6b7280'
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>', color, count
        )

    @admin.display(description='Published', ordering='_published')
    def published_count_badge(self, obj):
        count = getattr(obj, '_published', 0)
        color = '#10b981' if count > 0 else '#6b7280'
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>', color, count
        )

    @admin.display(description='Social')
    def social_links(self, obj):
        links = []
        if obj.twitter_url:
            links.append(
                format_html('<a href="{}" target="_blank" style="color:#60a5fa;">Twitter</a>', obj.twitter_url)
            )
        if obj.linkedin_url:
            links.append(
                format_html('<a href="{}" target="_blank" style="color:#60a5fa;">LinkedIn</a>', obj.linkedin_url)
            )
        return format_html(' · '.join(str(l) for l in links)) if links else format_html('<span style="color:#6b7280;">—</span>')


# ═══════════════════════════════════════════════════════════════════════════
#  LIVE UPDATE ADMIN  (standalone)
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(LiveUpdate)
class LiveUpdateAdmin(admin.ModelAdmin):
    list_display   = ('title', 'article_link', 'timestamp', 'created_at')
    list_filter    = ('timestamp',)
    search_fields  = ('title', 'content', 'article__title')
    ordering       = ('-timestamp',)
    date_hierarchy = 'timestamp'

    @admin.display(description='Article')
    def article_link(self, obj):
        if obj.article:
            url = reverse('admin:news_article_change', args=[obj.article.pk])
            return format_html(
                '<a href="{}" style="color:#93c5fd;">{}</a>',
                url,
                obj.article.title[:55] + ('…' if len(obj.article.title) > 55 else ''),
            )
        return '—'


# ═══════════════════════════════════════════════════════════════════════════
#  ARTICLE ADMIN  (main — full-featured newsroom panel)
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleAdminForm

    # ── List columns ───────────────────────────────────────────────────────
    list_display = (
        'thumbnail_preview',
        'title_with_flags',
        'colored_status',
        'import_badge',
        'category',
        'author_display',
        'views_badge',
        'word_count_display',
        'published_at',
        'frontend_url_link',
    )

    list_display_links = ('thumbnail_preview', 'title_with_flags')

    # ── Filters ────────────────────────────────────────────────────────────
    list_filter = (
        StatusFilter,
        ImportTypeFilter,
        ActivistDraftFilter,
        PublishDateFilter,
        FlagsFilter,
        HasImageFilter,
        SocialPostFilter,
        'category',
    )

    # ── Search ─────────────────────────────────────────────────────────────
    search_fields = (
        'title', 'original_title', 'description',
        'content', 'source_name', 'author__user__name',
        'meta_description',
    )

    prepopulated_fields    = {'slug': ('title',)}
    date_hierarchy         = 'published_at'
    inlines                = [LiveUpdateInline]
    autocomplete_fields    = ['author', 'category']
    show_full_result_count = True
    list_per_page          = 30

    actions = [
        'make_published',
        'make_draft',
        'regenerate_slug',
        'run_ai_import_now',
        'admin_force_trending',
        'admin_force_featured',
        'admin_remove_special_flags',
        'post_to_telegram_now',
        'export_as_csv',
    ]

    # ── Fieldsets ──────────────────────────────────────────────────────────
    fieldsets = (
        ('📰 Article Content', {
            'fields': (
                'title', 'slug', 'category', 'author',
                'description', 'content', 'featured_image', 'tags_input',
            ),
        }),
        ('📎 Writer Evidence & Notes', {
            'fields': ('supporting_document', 'writer_notes'),
            'description': (
                'Editorial team reviews these to verify author claims. '
                'Not publicly visible.'
            ),
        }),
        ('🤖 AI Import & Source Data', {
            'fields': (
                'is_imported', 'source_name', 'source_url',
                'original_title', 'meta_description', 'original_content',
            ),
            'classes': ('collapse',),
            'description': (
                'Auto-populated when article is imported via the GNews AI pipeline. '
                'Editing is not recommended.'
            ),
        }),
        ('⚙️ Settings & Flags', {
            'fields': (
                'status', 'published_at', 'views',
                'is_featured', 'is_trending', 'is_breaking',
                'is_editors_pick', 'is_top_story',
                'is_live', 'is_web_story',
            ),
        }),
        ('📢 Social Media Auto-Post', {
            'fields': ('post_to_facebook', 'post_to_twitter', 'post_to_telegram'),
            'description': 'Check platforms to post when article is Published.',
        }),
        ('🔒 System Trackers (Read Only)', {
            'fields': ('frontend_link', 'newsletter_sent', 'push_sent', 'web_story_created_at'),
            'classes': ('collapse',),
        }),
    )

    # ── Custom list_display columns ────────────────────────────────────────

    @admin.display(description='')
    def thumbnail_preview(self, obj):
        """Shows a small article thumbnail if a featured image exists."""
        if obj.featured_image:
            try:
                url = obj.featured_image.url
                return format_html(
                    '<img src="{}" style="width:56px;height:38px;object-fit:cover;'
                    'border-radius:5px;border:1px solid #334155;" />',
                    url,
                )
            except Exception:
                pass
        return format_html(
            '<div style="width:56px;height:38px;background:#1e293b;border-radius:5px;'
            'border:1px dashed #334155;display:flex;align-items:center;'
            'justify-content:center;font-size:16px;">📷</div>'
        )

    @admin.display(description='Title / Flags', ordering='title')
    def title_with_flags(self, obj):
        """Title with special flag badges below."""
        badges = []
        if obj.is_breaking:
            badges.append('<span style="background:#dc2626;color:#fff;padding:1px 6px;border-radius:4px;font-size:9px;font-weight:800;">BREAKING</span>')
        if obj.is_trending:
            badges.append('<span style="background:#d97706;color:#fff;padding:1px 6px;border-radius:4px;font-size:9px;font-weight:800;">TRENDING</span>')
        if obj.is_featured:
            badges.append('<span style="background:#7c3aed;color:#fff;padding:1px 6px;border-radius:4px;font-size:9px;font-weight:800;">FEATURED</span>')
        if obj.is_editors_pick:
            badges.append('<span style="background:#0284c7;color:#fff;padding:1px 6px;border-radius:4px;font-size:9px;font-weight:800;">PICK</span>')
        if obj.is_live:
            badges.append('<span style="background:#059669;color:#fff;padding:1px 6px;border-radius:4px;font-size:9px;font-weight:800;">LIVE</span>')

        title_html = format_html(
            '<span style="color:#e2e8f0;font-weight:600;font-size:13px;">{}</span>',
            obj.title[:80] + ('…' if len(obj.title) > 80 else ''),
        )
        if badges:
            badges_html = ' '.join(badges)
            return format_html('{}<br><span style="margin-top:3px;display:inline-block;">{}</span>', title_html, format_html(badges_html))
        return title_html

    @admin.display(description='Status', ordering='status')
    def colored_status(self, obj):
        if obj.status == 'published':
            return format_html(
                '<span style="background:#064e3b;color:#6ee7b7;padding:3px 10px;'
                'border-radius:20px;font-size:11px;font-weight:700;">Published</span>'
            )
        return format_html(
            '<span style="background:#451a03;color:#fcd34d;padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:700;">Draft</span>'
        )

    @admin.display(description='Type', ordering='is_imported')
    def import_badge(self, obj):
        if obj.is_imported:
            source = obj.source_name or 'GNews'
            return format_html(
                '<span style="background:#1e3a5f;color:#60a5fa;padding:3px 10px;'
                'border-radius:20px;font-size:11px;font-weight:700;" title="Source: {}">AI</span>',
                source,
            )
        return format_html(
            '<span style="background:#2e1065;color:#c4b5fd;padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:700;">Manual</span>'
        )

    @admin.display(description='Author', ordering='author__user__name')
    def author_display(self, obj):
        if obj.author:
            return format_html(
                '<span style="color:#94a3b8;font-size:12px;">{}</span>',
                obj.author.user.name or obj.author.user.email,
            )
        return format_html('<span style="color:#475569;">—</span>')

    @admin.display(description='Views', ordering='views')
    def views_badge(self, obj):
        v = obj.views or 0
        if v >= 1000:
            color = '#10b981'
        elif v >= 100:
            color = '#f59e0b'
        else:
            color = '#6b7280'
        return format_html(
            '<span style="color:{};font-weight:700;font-size:12px;">{}</span>',
            color,
            f'{v:,}',
        )

    @admin.display(description='Words / Read')
    def word_count_display(self, obj):
        wc = _word_count(obj.content)
        rt = _read_time(wc)
        if wc == 0:
            return format_html('<span style="color:#6b7280;font-size:11px;">—</span>')
        wc_color = '#10b981' if wc >= 700 else ('#f59e0b' if wc >= 400 else '#ef4444')
        return format_html(
            '<span style="color:{};font-size:11px;font-weight:700;">{} w</span>'
            '<span style="color:#64748b;font-size:10px;"> · {}</span>',
            wc_color, f'{wc:,}', rt,
        )

    @admin.display(description='Link')
    def frontend_url_link(self, obj):
        base_url = os.getenv('FRONTEND_URL', 'http://localhost').rstrip('/')
        if not obj.slug:
            return '—'
        url = f'{base_url}/article/{obj.slug}'
        return format_html(
            '<a href="{}" target="_blank" style="color:#60a5fa;font-size:11px;'
            'font-weight:600;white-space:nowrap;">View →</a>',
            url,
        )

    @admin.display(description='Frontend URL')
    def frontend_link(self, obj):
        if not obj.slug:
            return '—'
        base_url = os.getenv('FRONTEND_URL', 'http://localhost').rstrip('/')
        url = f'{base_url}/article/{obj.slug}'
        return format_html('<a href="{0}" target="_blank">{0}</a>', url)

    # ── Tags save logic ────────────────────────────────────────────────────
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        tags_string = form.cleaned_data.get('tags_input', '')
        instance    = form.instance
        if tags_string:
            tag_names = [n.strip() for n in tags_string.split(',') if n.strip()]
            tag_objs  = []
            for name in tag_names:
                slug = slugify(name)
                if slug:
                    tag_obj, _ = Tag.objects.get_or_create(slug=slug, defaults={'name': name[:50]})
                    tag_objs.append(tag_obj)
            instance.tags.set(tag_objs)
        else:
            instance.tags.clear()

    # ── Queryset (role-based visibility) ───────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return qs
        if hasattr(request.user, 'author_profile'):
            return qs.filter(author=request.user.author_profile)
        return qs.none()

    # ── Readonly fields (role-based) ───────────────────────────────────────
    def get_readonly_fields(self, request, obj=None):
        base = ('frontend_link', 'views', 'newsletter_sent', 'push_sent', 'web_story_created_at')
        user     = request.user
        is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
        is_editor = getattr(user, 'role', '') == 'editor'
        if is_admin:
            return base
        if is_editor:
            return base + ('is_breaking',)
        return base + ('author', 'is_featured', 'is_trending', 'is_breaking', 'is_editors_pick', 'is_top_story')

    # ── Save model ─────────────────────────────────────────────────────────
    def save_model(self, request, obj, form, change):
        if getattr(obj, 'author', None) is None and hasattr(request.user, 'author_profile'):
            obj.author = request.user.author_profile
        if not obj.slug:
            obj.slug = ''
        if change and form.instance.pk:
            user     = request.user
            is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
            if not is_admin:
                original = Article.objects.filter(pk=form.instance.pk).values('is_breaking').first()
                if original:
                    obj.is_breaking = original['is_breaking']
        super().save_model(request, obj, form, change)

    # ── Form (inject request) ──────────────────────────────────────────────
    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)
        original_init = Form.__init__
        def patched_init(self_form, *args, **kw):
            kw['request'] = request
            original_init(self_form, *args, **kw)
        Form.__init__ = patched_init
        return Form

    # ── List editable (inline toggles for admin/editor) ───────────────────
    def get_list_editable(self, request):
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return ('is_editors_pick', 'is_live')
        return ()

    def get_changelist_instance(self, request):
        self.list_editable = self.get_list_editable(request)
        return super().get_changelist_instance(request)

    # ════════════════════════════════════════════════════════════════════════
    #  BULK ACTIONS
    # ════════════════════════════════════════════════════════════════════════

    @admin.action(description='✅ Publish selected articles')
    def make_published(self, request, queryset):
        if not (request.user.role in ['admin', 'editor'] or request.user.is_superuser):
            self.message_user(request, '⛔ Permission denied.', level=messages.ERROR)
            return
        updated = 0
        for article in queryset.all():
            article.status = 'published'
            if not article.published_at:
                article.published_at = timezone_now()
            article.save()
            updated += 1
        self.message_user(request, f'✅ {updated} article(s) published successfully.')

    @admin.action(description='📋 Move selected articles to Draft')
    def make_draft(self, request, queryset):
        count = queryset.update(status='draft')
        self.message_user(request, f'📋 {count} article(s) moved to Draft.', level=messages.WARNING)

    @admin.action(description='🔄 Regenerate slug from title')
    def regenerate_slug(self, request, queryset):
        count = 0
        for article in queryset:
            article.slug = ''
            article.save()
            count += 1
        self.message_user(request, f'🔄 Slug regenerated for {count} article(s).')

    @admin.action(description='🤖 Run AI News Import Now (GNews → Research → Groq → Draft)')
    def run_ai_import_now(self, request, queryset):
        if not (request.user.role in ['admin', 'editor'] or request.user.is_superuser):
            self.message_user(request, '⛔ Permission denied.', level=messages.ERROR)
            return
        gnews_key = os.getenv('GNEWS_API_KEY')
        groq_key  = os.getenv('GROQ_API_KEY')
        if not gnews_key:
            self.message_user(request, '❌ GNEWS_API_KEY not configured in .env.', level=messages.ERROR)
            return
        if not groq_key:
            self.message_user(request, '❌ GROQ_API_KEY not configured.', level=messages.ERROR)
            return
        try:
            from news.tasks import auto_import_news_task
            auto_import_news_task.delay()
            self.message_user(
                request,
                '🤖 AI News Import queued in Celery! '
                'Exactly 2 research-backed articles will appear as Drafts in 5–15 minutes. '
                'Use the "AI Imported" filter to find them.',
                level=messages.SUCCESS,
            )
        except Exception as exc:
            self.message_user(request, f'❌ Could not queue import: {exc}', level=messages.ERROR)

    @admin.action(description='🔥 Force TRENDING on selected (Admin Override)')
    def admin_force_trending(self, request, queryset):
        if not (request.user.role == 'admin' or request.user.is_superuser):
            self.message_user(request, '⛔ Admins only.', level=messages.ERROR)
            return
        count = queryset.update(is_trending=True)
        self.message_user(request, f'🔥 {count} article(s) force-marked as Trending.')

    @admin.action(description='⭐ Force FEATURED on selected (Admin Override)')
    def admin_force_featured(self, request, queryset):
        if not (request.user.role == 'admin' or request.user.is_superuser):
            self.message_user(request, '⛔ Admins only.', level=messages.ERROR)
            return
        count = queryset.update(is_featured=True)
        self.message_user(request, f'⭐ {count} article(s) force-marked as Featured.')

    @admin.action(description='🗑️ Remove ALL special flags (Trending/Featured/Breaking)')
    def admin_remove_special_flags(self, request, queryset):
        if not (request.user.role == 'admin' or request.user.is_superuser):
            self.message_user(request, '⛔ Admins only.', level=messages.ERROR)
            return
        count = queryset.update(is_trending=False, is_featured=False, is_breaking=False, is_editors_pick=False, is_top_story=False)
        self.message_user(request, f'🗑️ All special flags cleared on {count} article(s).', level=messages.WARNING)

    @admin.action(description='✈️ Post selected article to Telegram NOW')
    def post_to_telegram_now(self, request, queryset):
        if not (request.user.role in ['admin', 'editor'] or request.user.is_superuser):
            self.message_user(request, '⛔ Admins/Editors only.', level=messages.ERROR)
            return
        tg_token   = os.getenv('TELEGRAM_BOT_TOKEN')
        tg_channel = os.getenv('TELEGRAM_CHANNEL_ID')
        if not tg_token or not tg_channel:
            self.message_user(request, '❌ Telegram credentials not configured in .env.', level=messages.ERROR)
            return
        queued = skipped = 0
        for article in queryset:
            if article.status != 'published':
                self.message_user(request, f'⚠️ "{article.title[:50]}" is not published — skipped.', level=messages.WARNING)
                skipped += 1
                continue
            Article.objects.filter(pk=article.pk).update(post_to_telegram=True)
            from news.tasks import auto_post_article_task
            auto_post_article_task.delay(article.id)
            queued += 1
        if queued:
            self.message_user(request, f'✈️ {queued} article(s) queued for Telegram.', level=messages.SUCCESS)

    @admin.action(description='📊 Export selected articles to CSV')
    def export_as_csv(self, request, queryset):
        """Exports selected articles as a downloadable CSV file."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ferox_times_articles.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Title', 'Status', 'Category', 'Author',
            'Published At', 'Views', 'Word Count', 'Is Imported',
            'Source Name', 'Source URL', 'Tags', 'Meta Description',
        ])
        for article in queryset.select_related('category', 'author__user').prefetch_related('tags'):
            wc   = _word_count(article.content)
            tags = ', '.join(t.name for t in article.tags.all())
            writer.writerow([
                article.pk,
                article.title,
                article.status,
                article.category.name if article.category else '',
                article.author.user.name if article.author else '',
                article.published_at.strftime('%Y-%m-%d %H:%M') if article.published_at else '',
                article.views or 0,
                wc,
                'Yes' if article.is_imported else 'No',
                article.source_name or '',
                article.source_url or '',
                tags,
                article.meta_description or '',
            ])
        return response

    # ── Dashboard warning banner ───────────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            ai_drafts = Article.objects.filter(is_imported=True, status='draft').count()
            if ai_drafts > 0:
                messages.warning(
                    request,
                    f'🤖 {ai_drafts} AI-imported article(s) are awaiting editorial review. '
                    f'Use the "AI Imported + Draft" filter to find them.',
                )

        if request.user.role in ['author', 'reporter'] and hasattr(request.user, 'author_profile'):
            ap    = request.user.author_profile
            total = Article.objects.filter(author=ap).count()
            pub   = Article.objects.filter(author=ap, status='published').count()
            draft = total - pub
            messages.info(
                request,
                f'📊 My Stats — Total: {total} | Published: {pub} | Draft: {draft}',
            )

        return super().changelist_view(request, extra_context=extra_context)