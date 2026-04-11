from django import forms
from django.contrib import admin
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify
from datetime import timedelta

from .models import Category, Author, Article, Tag, LiveUpdate


# ═══════════════════════════════════════════════════════════════════════════
#  CUSTOM LIST FILTERS  (with article counts in parentheses)
# ═══════════════════════════════════════════════════════════════════════════

class StatusFilter(admin.SimpleListFilter):
    """Filter by publication status — shows count for each option."""
    title = '📋 Status'
    parameter_name = 'article_status'   # Must NOT match model field name 'status'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        counts = {
            row['status']: row['c']
            for row in qs.values('status').annotate(c=Count('id'))
        }
        return [
            ('draft',     f'📝 Draft ({counts.get("draft", 0)})'),
            ('published', f'✅ Published ({counts.get("published", 0)})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'draft':
            return queryset.filter(status='draft')
        if self.value() == 'published':
            return queryset.filter(status='published')
        return queryset



class ImportTypeFilter(admin.SimpleListFilter):
    """Filter by article origin — AI imported vs manually written."""
    title = '🤖 Article Type'
    parameter_name = 'import_type'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        total     = qs.count()
        imported  = qs.filter(is_imported=True).count()
        manual    = qs.filter(is_imported=False).count()
        return [
            ('imported', f'🤖 AI Imported ({imported})'),
            ('manual',   f'✍️  Manual ({manual})'),
            ('all',      f'📰 All Articles ({total})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'imported':
            return queryset.filter(is_imported=True)
        if self.value() == 'manual':
            return queryset.filter(is_imported=False)
        return queryset


class PublishDateFilter(admin.SimpleListFilter):
    """Quick date-range filter for articles."""
    title = '📅 Published Date'
    parameter_name = 'pub_date'

    def lookups(self, request, model_admin):
        return [
            ('today',       '📆 Today'),
            ('yesterday',   '📆 Yesterday'),
            ('this_week',   '📆 This Week'),
            ('last_7',      '📆 Last 7 Days'),
            ('this_month',  '📆 This Month'),
            ('last_30',     '📆 Last 30 Days'),
            ('older',       '🗂️  Older'),
        ]

    def queryset(self, request, queryset):
        now   = timezone.now()
        today = now.date()

        if self.value() == 'today':
            return queryset.filter(published_at__date=today)
        if self.value() == 'yesterday':
            return queryset.filter(published_at__date=today - timedelta(days=1))
        if self.value() == 'this_week':
            week_start = today - timedelta(days=today.weekday())
            return queryset.filter(published_at__date__gte=week_start)
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
    """Filter by special article flags — Breaking, Trending, Featured, etc."""
    title = '🚩 Special Flags'
    parameter_name = 'flags'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        return [
            ('breaking',     f'🚨 Breaking News ({qs.filter(is_breaking=True).count()})'),
            ('trending',     f'🔥 Trending ({qs.filter(is_trending=True).count()})'),
            ('featured',     f'⭐ Featured ({qs.filter(is_featured=True).count()})'),
            ('editors_pick', f"✏️  Editor's Pick ({qs.filter(is_editors_pick=True).count()})"),
            ('top_story',    f'🏆 Top Story ({qs.filter(is_top_story=True).count()})'),
            ('live',         f'🔴 Live Blog ({qs.filter(is_live=True).count()})'),
            ('web_story',    f'📱 Web Story ({qs.filter(is_web_story=True).count()})'),
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
    """Filter articles by whether they have a featured image."""
    title = '🖼️  Featured Image'
    parameter_name = 'has_image'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        with_img    = qs.exclude(featured_image='').exclude(featured_image__isnull=True).count()
        without_img = qs.filter(Q(featured_image='') | Q(featured_image__isnull=True)).count()
        return [
            ('yes', f'✅ Has Image ({with_img})'),
            ('no',  f'❌ No Image ({without_img})'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(featured_image='').exclude(featured_image__isnull=True)
        if self.value() == 'no':
            return queryset.filter(Q(featured_image='') | Q(featured_image__isnull=True))
        return queryset


class SocialPostFilter(admin.SimpleListFilter):
    """Filter by social media posting status."""
    title = '📢 Social Media'
    parameter_name = 'social'

    def lookups(self, request, model_admin):
        return [
            ('pending_fb',  '📘 Facebook Pending'),
            ('pending_tw',  '🐦 Twitter Pending'),
            ('pending_tg',  '📨 Telegram Pending'),
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


# ═══════════════════════════════════════════════════════════════════════════
#  ARTICLE ADMIN FORM
# ═══════════════════════════════════════════════════════════════════════════

class ArticleAdminForm(forms.ModelForm):
    tags_input = forms.CharField(
        max_length=500,
        required=False,
        label='Tags',
        help_text='Tags ko comma (,) ke sath likhein. Jaise: Sports, Cricket, Live News. '
                  'Naye tags apne aap ban jayenge aur existing select ho jayenge.'
    )

    class Meta:
        model = Article
        exclude = ('tags',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(
                [tag.name for tag in self.instance.tags.all()]
            )


# ═══════════════════════════════════════════════════════════════════════════
#  CUSTOM EXTENDED FILTERS
# ═══════════════════════════════════════════════════════════════════════════

class ActivistDraftFilter(admin.SimpleListFilter):
    """Filter to quickly find articles submitted by Independent Journalism Contributors (Authors) that need editorial review."""
    title = '✍️ Independent Contributor Drafts'
    parameter_name = 'activist_drafts'

    def lookups(self, request, model_admin):
        return [
            ('pending_review', '🚨 Pending Review (Drafts)'),
            ('published', '✅ Published by Guests'),
        ]

    def queryset(self, request, queryset):
        # Authors refer to the Independent Journalism Contributors
        if self.value() == 'pending_review':
            return queryset.filter(status='draft', author__user__role='author')
        if self.value() == 'published':
            return queryset.filter(status='published', author__user__role='author')
        return queryset

# ═══════════════════════════════════════════════════════════════════════════
#  INLINES
# ═══════════════════════════════════════════════════════════════════════════

class LiveUpdateInline(admin.StackedInline):
    model = LiveUpdate
    extra = 1
    fields = ('title', 'timestamp', 'content')


# ═══════════════════════════════════════════════════════════════════════════
#  CATEGORY / TAG / AUTHOR ADMINS
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role')
    search_fields = ('user__name', 'user__email', 'role')
    autocomplete_fields = ['user']


# ═══════════════════════════════════════════════════════════════════════════
#  ARTICLE ADMIN (main)
# ═══════════════════════════════════════════════════════════════════════════

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleAdminForm

    # ── List view columns ──────────────────────────────────────────────────
    list_display = (
        'title', 'colored_status', 'import_badge',
        'category', 'author',
        'published_at', 'views',
        'is_breaking', 'is_editors_pick', 'is_live',
    )

    # ── Comprehensive Filter Sidebar ───────────────────────────────────────
    list_filter = (
        StatusFilter,       # 📋 Draft / Published   (with counts)
        ImportTypeFilter,   # 🤖 AI Imported / Manual (with counts)
        ActivistDraftFilter,# ✍️ Pending Independent Contributor Drafts
        PublishDateFilter,  # 📅 Today / This Week / Last 30 days …
        FlagsFilter,        # 🚩 Breaking / Trending / Featured …
        HasImageFilter,     # 🖼️  Has Image / No Image
        SocialPostFilter,   # 📢 Facebook/Twitter/Telegram pending
        'category',         # Django built-in (category name list)
    )

    # ── Search ────────────────────────────────────────────────────────────
    search_fields = (
        'title', 'original_title', 'description',
        'content', 'source_name', 'author__user__name',
    )

    # ── Slug auto-fill via JS (Add mode only) ─────────────────────────────
    prepopulated_fields = {'slug': ('title',)}

    date_hierarchy      = 'published_at'
    inlines             = [LiveUpdateInline]
    autocomplete_fields = ['author', 'category']
    show_full_result_count = True

    actions = ['make_published', 'make_draft', 'regenerate_slug', 'run_ai_import_now']

    # ── Fieldsets ─────────────────────────────────────────────────────────
    fieldsets = (
        ('📝 Article Content', {
            'fields': ('title', 'slug', 'category', 'author',
                       'description', 'content', 'featured_image', 'tags_input')
        }),
        ('🤖 AI Import & Source Data', {
            'fields': ('is_imported', 'source_name', 'source_url',
                       'original_title', 'meta_description', 'original_content'),
            'classes': ('collapse',),
            'description': 'Auto-populated when article is imported via AI. Editing not recommended.',
        }),
        ('⚙️ Settings & Flags', {
            'fields': ('status', 'published_at', 'views',
                       'is_featured', 'is_trending', 'is_breaking',
                       'is_editors_pick', 'is_top_story',
                       'is_live', 'is_web_story'),
        }),
        ('🚀 Social Media Auto-Post', {
            'fields': ('post_to_facebook', 'post_to_twitter', 'post_to_telegram'),
            'description': 'Article "Published" status mein save karne par auto-post hoga.',
        }),
        ('🔒 System Trackers (Read Only)', {
            'fields': ('newsletter_sent', 'push_sent', 'web_story_created_at'),
            'classes': ('collapse',),
        }),
    )

    # ── Custom list_display columns ────────────────────────────────────────

    @admin.display(description='Status', ordering='status')
    def colored_status(self, obj):
        if obj.status == 'published':
            return format_html(
                '<span style="color:#27ae60;font-weight:bold;">✅ Published</span>'
            )
        return format_html(
            '<span style="color:#e67e22;font-weight:bold;">📝 Draft</span>'
        )

    @admin.display(description='Type', ordering='is_imported')
    def import_badge(self, obj):
        if obj.is_imported:
            # Show source name too for AI imports
            source = obj.source_name or "GNews"
            return format_html(
                '<span style="background:#2980b9;color:#fff;padding:2px 7px;'
                'border-radius:4px;font-size:11px;" title="Source: {}">🤖 AI</span>',
                source,
            )
        return format_html(
            '<span style="background:#8e44ad;color:#fff;padding:2px 7px;'
            'border-radius:4px;font-size:11px;">✍️ Manual</span>'
        )

    # ── Tags logic ─────────────────────────────────────────────────────────
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        tags_string = form.cleaned_data.get('tags_input', '')
        instance    = form.instance

        if tags_string:
            tag_names = [name.strip() for name in tags_string.split(',') if name.strip()]
            tag_objs  = []
            for name in tag_names:
                slug = slugify(name)
                if slug:
                    tag_obj, _ = Tag.objects.get_or_create(slug=slug, defaults={'name': name[:50]})
                    tag_objs.append(tag_obj)
            instance.tags.set(tag_objs)
        else:
            instance.tags.clear()

    # ── Bulk Actions ───────────────────────────────────────────────────────

    @admin.action(description='✅ Publish selected articles')
    def make_published(self, request, queryset):
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            count = queryset.update(status='published')
            self.message_user(request, f'✅ {count} article(s) published.')
        else:
            self.message_user(request, "Permission denied.", level='error')

    @admin.action(description='📝 Move selected articles to Draft')
    def make_draft(self, request, queryset):
        count = queryset.update(status='draft')
        self.message_user(request, f'📝 {count} article(s) moved to draft.')

    @admin.action(description='🔄 Regenerate slug from title')
    def regenerate_slug(self, request, queryset):
        """
        Clears slug → Article.save() regenerates from current title.
        ⚠️ Do NOT use on published articles without 301 redirects.
        """
        count = 0
        for article in queryset:
            article.slug = ''
            article.save()
            count += 1
        self.message_user(request, f'🔄 Slug regenerated for {count} article(s).')

    @admin.action(description='🤖 Run AI News Import Now (GNews → Groq → Draft)')
    def run_ai_import_now(self, request, queryset):
        """
        Manually triggers the GNews → scrape → Groq → draft pipeline.
        Useful when admin wants to import news on demand without waiting
        for the 30-minute Celery Beat schedule.
        """
        if not (request.user.role in ['admin', 'editor'] or request.user.is_superuser):
            self.message_user(
                request,
                "⛔ Permission denied. Only Admins and Editors can trigger AI import.",
                level=messages.ERROR,
            )
            return

        import os
        gnews_key = os.getenv("GNEWS_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        if not gnews_key:
            self.message_user(
                request,
                "❌ GNEWS_API_KEY is not configured in the environment. Please set it in your .env file.",
                level=messages.ERROR,
            )
            return

        if not groq_key:
            self.message_user(
                request,
                "❌ GROQ_API_KEY is not configured. AI rewriting is disabled.",
                level=messages.ERROR,
            )
            return

        try:
            from news.tasks import auto_import_news_task
            auto_import_news_task.delay()
            self.message_user(
                request,
                "🤖 AI News Import has been queued in Celery! "
                "New articles will appear as Drafts within 2–5 minutes. "
                "Use the '🤖 AI Imported' filter to find them.",
                level=messages.SUCCESS,
            )
        except Exception as exc:
            self.message_user(
                request,
                f"❌ Could not queue AI import task: {exc}",
                level=messages.ERROR,
            )

    # ── Queryset (role-based) ──────────────────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return qs
        if hasattr(request.user, 'author_profile'):
            return qs.filter(author=request.user.author_profile)
        return qs.none()

    # ── Readonly fields ────────────────────────────────────────────────────
    def get_readonly_fields(self, request, obj=None):
        base = ('views', 'newsletter_sent', 'push_sent', 'web_story_created_at')
        if request.user.role in ['author', 'reporter'] and not request.user.is_superuser:
            return base + ('author', 'is_featured', 'is_trending',
                           'is_breaking', 'is_editors_pick', 'is_top_story')
        return base

    # ── Save model ─────────────────────────────────────────────────────────
    def save_model(self, request, obj, form, change):
        if getattr(obj, 'author', None) is None and hasattr(request.user, 'author_profile'):
            obj.author = request.user.author_profile
        if not obj.slug:
            obj.slug = ''   # blank → Article.save() will regenerate from title
        super().save_model(request, obj, form, change)

    # ── List editable (inline status toggle) ──────────────────────────────
    def get_list_editable(self, request):
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return ('is_editors_pick', 'is_live')
        return ()

    def get_changelist_instance(self, request):
        self.list_editable = self.get_list_editable(request)
        return super().get_changelist_instance(request)

    # ── Changelist dashboard message ───────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        # Show pending AI drafts notice to admins/editors
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            ai_drafts = Article.objects.filter(is_imported=True, status='draft').count()
            if ai_drafts > 0:
                messages.warning(
                    request,
                    f'📥 {ai_drafts} AI-imported article(s) are waiting for your review! '
                    f'Please review and publish them. '
                    f'[Filter: Article Type → 🤖 AI Imported + Status → 📝 Draft]'
                )

        if request.user.role in ['author', 'reporter'] and hasattr(request.user, 'author_profile'):
            ap      = request.user.author_profile
            total   = Article.objects.filter(author=ap).count()
            pub     = Article.objects.filter(author=ap, status='published').count()
            draft   = total - pub
            messages.info(
                request,
                f'📊 MY STATS  |  Total: {total}  |  ✅ Published: {pub}  |  📝 Draft: {draft}'
            )
        return super().changelist_view(request, extra_context=extra_context)