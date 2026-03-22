from django.contrib import admin
from django.contrib import messages
from .models import Category, Author, Article, Tag, LiveUpdate



class LiveUpdateInline(admin.StackedInline):
    model = LiveUpdate
    extra = 1 # Ek khali box hamesha dikhega naya update daalne ke liye
    fields = ('title', 'timestamp', 'content')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'status', 'published_at', 'views', 'is_editors_pick', 'is_top_story', 'is_live', 'is_web_story')
    list_filter = ('status', 'category', 'is_featured', 'is_trending', 'is_top_story','is_web_story')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)


    inlines = [LiveUpdateInline]

    # ==========================================
    # AUTHOR DASHBOARD & PERMISSIONS LOGIC
    # ==========================================

    fieldsets = (
        ('📝 Article Content', {
            'fields': ('title', 'slug', 'category', 'author', 'source_name', 'description', 'content', 'featured_image', 'tags')
        }),
        ('⚙️ Settings & Flags', {
            'fields': ('status', 'published_at', 'views', 'is_featured', 'is_trending', 'is_breaking', 'is_editors_pick', 'is_top_story', 'is_live', 'is_web_story')
        }),
        ('🚀 Social Media Auto-Post', {
            'fields': ('post_to_facebook', 'post_to_twitter', 'post_to_telegram'),
            'description': 'Article "Published" status mein save karne par, in tick kiye hue platforms par auto-post ho jayega.'
        }),
    )



    def get_queryset(self, request):
        """Sirf apne articles dikhane ke liye"""
        qs = super().get_queryset(request)
        # Agar admin ya editor hai, toh saare articles dikhao
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return qs
        
        # Agar author/reporter hai, toh sirf uske articles dikhao
        if hasattr(request.user, 'author_profile'):
            return qs.filter(author=request.user.author_profile)
        
        return qs.none()

    def get_readonly_fields(self, request, obj=None):
        """Author ko views aur premium flags edit karne se rokne ke liye"""
        if request.user.role in ['author', 'reporter'] and not request.user.is_superuser:
            # Author in fields ko sirf dekh sakta hai, change nahi kar sakta
            return ('author', 'views', 'is_featured', 'is_trending', 'is_breaking', 'is_editors_pick')
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        """Article save karte waqt automatically current author ko assign karne ke liye"""
        if getattr(obj, 'author', None) is None and hasattr(request.user, 'author_profile'):
            obj.author = request.user.author_profile
        super().save_model(request, obj, form, change)

    def get_list_editable(self, request):
        """List se directly edit karne ka option sirf Admins ko dene ke liye"""
        if request.user.role in ['admin', 'editor'] or request.user.is_superuser:
            return ('is_editors_pick',)
        return () # Authors ke liye koi list editable nahi hogi

    def get_changelist_instance(self, request):
        """Django ko dynamic list_editable batane ke liye"""
        self.list_editable = self.get_list_editable(request)
        return super().get_changelist_instance(request)

    def changelist_view(self, request, extra_context=None):
        """Dashboard jaisi feeling dene ke liye upar Stats (Views/Articles) dikhana"""
        if request.user.role in ['author', 'reporter'] and hasattr(request.user, 'author_profile'):
            author_profile = request.user.author_profile
            
            # Author ke stats calculate karein
            total_articles = Article.objects.filter(author=author_profile).count()
            published_articles = Article.objects.filter(author=author_profile, status='published').count()
            
            # Unke sabhi articles ke total views
            articles_views = Article.objects.filter(author=author_profile).values_list('views', flat=True)
            total_views = sum(articles_views) if articles_views else 0
            
            # Top par ek sundar message banner dikhayein
            messages.info(
                request, 
                f"📊 MY DASHBOARD | Total Articles: {total_articles} | Published: {published_articles} | Total Views: {total_views}"
            )
            
        return super().changelist_view(request, extra_context=extra_context)
    
