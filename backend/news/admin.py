from django import forms
from django.contrib import admin
from django.contrib import messages
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify
from datetime import timedelta

from .models import Category, Author, Article, Tag, LiveUpdate
from django.utils.timezone import now as timezone_now


# ═══════════════════════════════════════════════════════════════════════════
#  CUSTOM LIST FILTERS  (with article counts in parentheses)
# ═══════════════════════════════════════════════════════════════════════════

class StatusFilter(admin.SimpleListFilter):
    """Filter by publication status."""
    title = 'Status'
    parameter_name = 'article_status'

    def lookups(self, request, model_admin):
        return [
            ('draft',     'Draft'),
            ('published', 'Published'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'draft':
            return queryset.filter(status='draft')
        if self.value() == 'published':
            return queryset.filter(status='published')
        return queryset


class ImportTypeFilter(admin.SimpleListFilter):
    """Filter by article origin — AI imported vs manually written."""
    title = 'Article Type'
    parameter_name = 'import_type'

    def lookups(self, request, model_admin):
        return [
            ('imported', 'AI Imported'),
            ('manual',   'Manual'),
            ('all',      'All Articles'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'imported':
            return queryset.filter(is_imported=True)
        if self.value() == 'manual':
            return queryset.filter(is_imported=False)
        return queryset


class PublishDateFilter(admin.SimpleListFilter):
    """Quick date-range filter for articles."""
    title = 'Published Date'
    parameter_name = 'pub_date'

    def lookups(self, request, model_admin):
        return [
            ('today',       'Today'),
            ('yesterday',   'Yesterday'),
            ('this_week',   'This Week'),
            ('last_7',      'Last 7 Days'),
            ('this_month',  'This Month'),
            ('last_30',     'Last 30 Days'),
            ('older',       'Older'),
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
    title = 'Special Flags'
    parameter_name = 'flags'

    def lookups(self, request, model_admin):
        return [
            ('breaking',     'Breaking News'),
            ('trending',     'Trending'),
            ('featured',     'Featured'),
            ('editors_pick', "Editor's Pick"),
            ('top_story',    'Top Story'),
            ('live',         'Live Blog'),
            ('web_story',    'Web Story'),
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
    title = 'Featured Image'
    parameter_name = 'has_image'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'Has Image'),
            ('no',  'No Image'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(featured_image='').exclude(featured_image__isnull=True)
        if self.value() == 'no':
            return queryset.filter(Q(featured_image='') | Q(featured_image__isnull=True))
        return queryset


class SocialPostFilter(admin.SimpleListFilter):
    """Filter by social media posting status."""
    title = 'Social Media'
    parameter_name = 'social'

    def lookups(self, request, model_admin):
        return [
            ('pending_fb',  'Facebook Pending'),
            ('pending_tw',  'Twitter Pending'),
            ('pending_tg',  'Telegram Pending'),
            ('push_sent',   'Push Sent'),
            ('push_unsent', 'Push Not Sent'),
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
        self._request = kwargs.pop('request', None)  # Custom: request inject
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['tags_input'].initial = ', '.join(
                [tag.name for tag in self.instance.tags.all()]
            )

    def clean_is_breaking(self):
        """
        Security: Sirf Admin/Superuser is_breaking=True set kar sakta hai.
        Agar editor ya koi aur True karne ki koshish kare, raise ValidationError.
        """
        value = self.cleaned_data.get('is_breaking', False)
        request = self._request
        if value and request:
            user = request.user
            is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
            if not is_admin:
                raise forms.ValidationError(
                    "⛔ Sirf Admin is_breaking flag set kar sakta hai. "
                    "Editor aur Reporter ye flag set nahi kar sakte."
                )
        return value


# ═══════════════════════════════════════════════════════════════════════════
#  CUSTOM EXTENDED FILTERS
# ═══════════════════════════════════════════════════════════════════════════

class ActivistDraftFilter(admin.SimpleListFilter):
    """Filter to quickly find articles submitted by Independent Journalism Contributors (Authors) that need editorial review."""
    title = 'Independent Contributor Drafts'
    parameter_name = 'activist_drafts'

    def lookups(self, request, model_admin):
        return [
            ('pending_review', 'Pending Review (Drafts)'),
            ('published', 'Published by Guests'),
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
        'frontend_url_link',
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

    actions = [
        'make_published', 'make_draft', 'regenerate_slug', 'run_ai_import_now',
        'admin_force_trending', 'admin_force_featured', 'admin_remove_special_flags',
        'post_to_telegram_now',
    ]

    # ── Fieldsets ─────────────────────────────────────────────────────────
    fieldsets = (
        ('Article Content', {
            'fields': ('title', 'slug', 'category', 'author',
                       'description', 'content', 'featured_image', 'tags_input')
        }),
        ('Writer Evidence & Notes', {
            'fields': ('supporting_document', 'writer_notes'),
            'description': 'Editorial team reviews these to verify writer claims. Not publicly visible.',
        }),
        ('AI Import & Source Data', {
            'fields': ('is_imported', 'source_name', 'source_url',
                       'original_title', 'meta_description', 'original_content'),
            'classes': ('collapse',),
            'description': 'Auto-populated when article is imported via AI. Editing not recommended.',
        }),
        ('Settings & Flags', {
            'fields': ('status', 'published_at', 'views',
                       'is_featured', 'is_trending', 'is_breaking',
                       'is_editors_pick', 'is_top_story',
                       'is_live', 'is_web_story'),
        }),
        ('Social Media Auto-Post', {
            'fields': ('post_to_facebook', 'post_to_twitter', 'post_to_telegram'),
            'description': 'Social media platforms to post to. Will post when status is set to Published.',
        }),
        ('System Trackers (Read Only)', {
            'fields': ('frontend_link', 'newsletter_sent', 'push_sent', 'web_story_created_at'),
            'classes': ('collapse',),
        }),
    )

    # ── Custom list_display columns ────────────────────────────────────────

    @admin.display(description='Link')
    def frontend_url_link(self, obj):
        import os
        base_url = os.getenv('FRONTEND_URL', 'http://localhost').rstrip('/')
        if not obj.slug:
            return "-"
        url = f"{base_url}/article/{obj.slug}"
        return format_html('<a href="{}" target="_blank">View</a>', url)

    @admin.display(description='Frontend URL')
    def frontend_link(self, obj):
        if not obj.slug:
            return "-"
        import os
        base_url = os.getenv('FRONTEND_URL', 'http://localhost').rstrip('/')
        url = f"{base_url}/article/{obj.slug}"
        return format_html('<a href="{0}" target="_blank">{0}</a>', url)

    @admin.display(description='Status', ordering='status')
    def colored_status(self, obj):
        if obj.status == 'published':
            return format_html('<span style="color:#10b981;font-weight:bold;">Published</span>')
        return format_html('<span style="color:#d97706;font-weight:bold;">Draft</span>')

    @admin.display(description='Type', ordering='is_imported')
    def import_badge(self, obj):
        if obj.is_imported:
            source = obj.source_name or "GNews"
            return format_html('<span style="color:#2563eb;font-weight:bold;" title="Source: {}">AI</span>', source)
        return format_html('<span style="color:#7c3aed;font-weight:bold;">Manual</span>')

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

    @admin.action(description='Publish selected articles')
    def make_published(self, request, queryset):
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            updated = 0
            # Remove status__in filter because it's redundant and blocks some edges
            for article in queryset.all():
                article.status = 'published'
                # Auto published_at agar set nahi hai
                if not article.published_at:
                    article.published_at = timezone_now()
                # Use standard save() so custom overrides in models.py execute correctly
                article.save()
                updated += 1
            self.message_user(request, f'{updated} article(s) published.')
        else:
            self.message_user(request, "Permission denied.", level='error')

    @admin.action(description='Move selected articles to Draft')
    def make_draft(self, request, queryset):
        count = queryset.update(status='draft')
        self.message_user(request, f'{count} article(s) moved to draft.')

    @admin.action(description='Regenerate slug from title')
    def regenerate_slug(self, request, queryset):
        """
        Clears slug → Article.save() regenerates from current title.
        Do NOT use on published articles without 301 redirects.
        """
        count = 0
        for article in queryset:
            article.slug = ''
            article.save()
            count += 1
        self.message_user(request, f'Slug regenerated for {count} article(s).')

    @admin.action(description='Run AI News Import Now (GNews → Groq → Draft)')
    def run_ai_import_now(self, request, queryset):
        """
        Manually triggers the GNews → scrape → Groq → draft pipeline.
        Useful when admin wants to import news on demand without waiting
        for the 30-minute Celery Beat schedule.
        """
        if not (request.user.role in ['admin', 'editor'] or request.user.is_superuser):
            self.message_user(
                request,
                "Permission denied. Only Admins and Editors can trigger AI import.",
                level=messages.ERROR,
            )
            return

        import os
        gnews_key = os.getenv("GNEWS_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        if not gnews_key:
            self.message_user(
                request,
                "GNEWS_API_KEY is not configured in the environment. Please set it in your .env file.",
                level=messages.ERROR,
            )
            return

        if not groq_key:
            self.message_user(
                request,
                "GROQ_API_KEY is not configured. AI rewriting is disabled.",
                level=messages.ERROR,
            )
            return

        try:
            from news.tasks import auto_import_news_task
            auto_import_news_task.delay()
            self.message_user(
                request,
                "AI News Import has been queued in Celery! "
                "New articles will appear as Drafts within 2–5 minutes. "
                "Use the 'AI Imported' filter to find them.",
                level=messages.SUCCESS,
            )
        except Exception as exc:
            self.message_user(
                request,
                f"Could not queue AI import task: {exc}",
                level=messages.ERROR,
            )

    # ─────────────── Admin-Only Flag Override Actions ────────────────

    @admin.action(description='Force TRENDING on selected (Admin Override)')
    def admin_force_trending(self, request, queryset):
        if not (request.user.role == 'admin' or request.user.is_superuser):
            self.message_user(request, "Permission denied. Only Admins can do this.", level=messages.ERROR)
            return
        count = queryset.update(is_trending=True)
        self.message_user(request, f"{count} article(s) force-marked as Trending. (Admin Override)")

    @admin.action(description='Force FEATURED on selected (Admin Override)')
    def admin_force_featured(self, request, queryset):
        if not (request.user.role == 'admin' or request.user.is_superuser):
            self.message_user(request, "Permission denied. Only Admins can do this.", level=messages.ERROR)
            return
        count = queryset.update(is_featured=True)
        self.message_user(request, f"{count} article(s) force-marked as Featured. (Admin Override)")

    @admin.action(description='Remove ALL special flags from selected (Trending/Featured/Breaking)')
    def admin_remove_special_flags(self, request, queryset):
        if not (request.user.role == 'admin' or request.user.is_superuser):
            self.message_user(request, "Permission denied. Only Admins can do this.", level=messages.ERROR)
            return
        count = queryset.update(is_trending=False, is_featured=False, is_breaking=False)
        self.message_user(
            request,
            f"{count} article(s) had special flags cleared.",
            level=messages.WARNING,
        )

    @admin.action(description='Post selected article to Telegram NOW')
    def post_to_telegram_now(self, request, queryset):
        if not (request.user.role in ['admin', 'editor'] or request.user.is_superuser):
            self.message_user(request, "Permission denied. Only Admins/Editors can do this.", level=messages.ERROR)
            return

        import os
        tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
        tg_channel = os.getenv("TELEGRAM_CHANNEL_ID")

        if not tg_token or not tg_channel:
            self.message_user(
                request,
                "TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID missing in .env!",
                level=messages.ERROR,
            )
            return

        queued = 0
        skipped = 0
        for article in queryset:
            if article.status != 'published':
                self.message_user(
                    request,
                    f"'{article.title[:50]}' is not published — skipped.",
                    level=messages.WARNING,
                )
                skipped += 1
                continue
            Article.objects.filter(pk=article.pk).update(post_to_telegram=True)
            from news.tasks import auto_post_article_task
            auto_post_article_task.delay(article.id)
            queued += 1

        if queued:
            self.message_user(
                request,
                f"{queued} article(s) queued for Telegram posting!",
                level=messages.SUCCESS,
            )

    # ── Queryset (role-based) ──────────────────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return qs
        if hasattr(request.user, 'author_profile'):
            return qs.filter(author=request.user.author_profile)
        return qs.none()

    # ── Readonly fields ─────────────────────────────────────────────
    def get_readonly_fields(self, request, obj=None):
        base = ('frontend_link', 'views', 'newsletter_sent', 'push_sent', 'web_story_created_at')

        user = request.user
        is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
        is_editor = getattr(user, 'role', '') == 'editor'

        if is_admin:
            # Admin sab kuch edit kar sakta hai, sirf system trackers readonly hain
            return base

        if is_editor:
            # Editor is_breaking set NAHI kar sakta — wo admin-only flag hai
            return base + ('is_breaking',)

        # Author / Reporter: sabhi flags readonly hain
        return base + ('author', 'is_featured', 'is_trending',
                       'is_breaking', 'is_editors_pick', 'is_top_story')

    # ── Save model ───────────────────────────────────────────────
    def save_model(self, request, obj, form, change):
        if getattr(obj, 'author', None) is None and hasattr(request.user, 'author_profile'):
            obj.author = request.user.author_profile
        if not obj.slug:
            obj.slug = ''   # blank → Article.save() will regenerate from title
        # Extra guard: editor ne kisi tarah is_breaking True kar diya?
        # Force it back to the original value if they are not admin.
        if change and form.instance.pk:
            user = request.user
            is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
            if not is_admin:
                # Previous value se compare karo
                original = Article.objects.filter(pk=form.instance.pk).values('is_breaking').first()
                if original and not is_admin:
                    obj.is_breaking = original['is_breaking']
        super().save_model(request, obj, form, change)

    # ── List editable (inline status toggle) ──────────────────────────────
    def get_list_editable(self, request):
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return ('is_editors_pick', 'is_live')
        return ()

    def get_form(self, request, obj=None, **kwargs):
        """
        ArticleAdminForm ko request inject karo taaki clean_is_breaking
        mein user ka role check ho sake.
        """
        Form = super().get_form(request, obj, **kwargs)

        # Closure: request bind karo factory method se create hone wala form class mein
        original_init = Form.__init__

        def patched_init(self_form, *args, **kw):
            kw['request'] = request
            original_init(self_form, *args, **kw)

        Form.__init__ = patched_init
        return Form

    def get_changelist_instance(self, request):
        self.list_editable = self.get_list_editable(request)
        return super().get_changelist_instance(request)

    # ── Changelist dashboard message ───────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Inject AI Article Writer button URL for admins / editors
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            extra_context['ai_writer_url'] = '/admin/news/ai-writer/'
            extra_context['show_ai_writer_button'] = True

            ai_drafts = Article.objects.filter(is_imported=True, status='draft').count()
            if ai_drafts > 0:
                messages.warning(
                    request,
                    f'{ai_drafts} AI-imported article(s) are waiting for your review! '
                    f'Please review and publish them.'
                )

        if request.user.role in ['author', 'reporter'] and hasattr(request.user, 'author_profile'):
            ap      = request.user.author_profile
            total   = Article.objects.filter(author=ap).count()
            pub     = Article.objects.filter(author=ap, status='published').count()
            draft   = total - pub
            messages.info(
                request,
                f'MY STATS | Total: {total} | Published: {pub} | Draft: {draft}'
            )
        return super().changelist_view(request, extra_context=extra_context)