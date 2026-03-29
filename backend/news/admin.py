from django.contrib import admin
from django.contrib import messages
from .models import Category, Author, Article, Tag, LiveUpdate

class LiveUpdateInline(admin.StackedInline):
    model = LiveUpdate
    extra = 1
    fields = ('title', 'timestamp', 'content')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    search_fields = ('user__name', 'user__email', 'role')
    autocomplete_fields = ['user']

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'status', 'published_at', 'views', 'is_editors_pick', 'is_live')
    list_filter = ('status', 'category', 'is_featured', 'is_breaking', 'is_editors_pick', 'is_live', 'published_at')
    search_fields = ('title', 'content', 'description', 'author__user__name')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    date_hierarchy = 'published_at'
    inlines = [LiveUpdateInline]
    autocomplete_fields = ['author', 'category'] # Fast loading for large databases
    
    actions = ['make_published', 'make_draft']

    fieldsets = (
        ('📝 Article Content', {
            'fields': ('title', 'slug', 'category', 'author', 'source_name', 'description', 'content', 'featured_image', 'tags')
        }),
        ('⚙️ Settings & Flags', {
            'fields': ('status', 'published_at', 'views', 'is_featured', 'is_trending', 'is_breaking', 'is_editors_pick', 'is_top_story', 'is_live', 'is_web_story')
        }),
        ('🚀 Social Media Auto-Post', {
            'fields': ('post_to_facebook', 'post_to_twitter', 'post_to_telegram'),
            'description': 'Article "Published" status mein save karne par, in platforms par auto-post ho jayega.'
        }),
        ('System Trackers (Read Only)', {
            'fields': ('newsletter_sent', 'push_sent', 'web_story_created_at'),
            'classes': ('collapse',), # Hide by default
        })
    )

    @admin.action(description='✅ Publish selected articles')
    def make_published(self, request, queryset):
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            queryset.update(status='published')
        else:
            self.message_user(request, "You don't have permission to bulk publish.", level='error')

    @admin.action(description='📝 Move selected articles to Draft')
    def make_draft(self, request, queryset):
        queryset.update(status='draft')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return qs
        if hasattr(request.user, 'author_profile'):
            return qs.filter(author=request.user.author_profile)
        return qs.none()

    def get_readonly_fields(self, request, obj=None):
        base_readonly = ('views', 'newsletter_sent', 'push_sent', 'web_story_created_at')
        if request.user.role in ['author', 'reporter'] and not request.user.is_superuser:
            return base_readonly + ('author', 'is_featured', 'is_trending', 'is_breaking', 'is_editors_pick', 'is_top_story')
        return base_readonly

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'author', None) is None and hasattr(request.user, 'author_profile'):
            obj.author = request.user.author_profile
        super().save_model(request, obj, form, change)

    def get_list_editable(self, request):
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return ('status', 'is_editors_pick', 'is_live')
        return ()

    def get_changelist_instance(self, request):
        self.list_editable = self.get_list_editable(request)
        return super().get_changelist_instance(request)

    def changelist_view(self, request, extra_context=None):
        if request.user.role in ['author', 'reporter'] and hasattr(request.user, 'author_profile'):
            author_profile = request.user.author_profile
            total_articles = Article.objects.filter(author=author_profile).count()
            published_articles = Article.objects.filter(author=author_profile, status='published').count()
            
            messages.info(request, f"📊 MY DASHBOARD | Total Articles: {total_articles} | Published: {published_articles}")
        return super().changelist_view(request, extra_context=extra_context)