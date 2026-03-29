from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.db import models
from django.utils.text import slugify
from tinymce.models import HTMLField
from core.models import BaseModel
from users.models import User
from django.utils import timezone
from django.db import models
from django.utils.text import slugify
from tinymce.models import HTMLField
from core.models import BaseModel
from users.models import User
from django.utils import timezone


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Author(BaseModel):
    """
    Agar koi user author hai toh uski extra details. (author.js ke mutabiq)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
    role = models.CharField(max_length=100, help_text="e.g. Senior Tech Reporter")
    twitter_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.user.name
    


class Tag(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Article(BaseModel):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='articles')
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, related_name='articles')
    
    # External sources (e.g. BBC News, TechCrunch)
    source_name = models.CharField(max_length=100, blank=True, null=True)
    
    description = models.TextField(help_text="Short excerpt for homepage")
    # content = models.TextField(help_text="Full article content")
    content = HTMLField(help_text="Full article content with rich text editor")
    
    featured_image = models.ImageField(upload_to='articles/images/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, related_name='articles', blank=True)
    # Frontend flags & stats
    views = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, help_text="Show in large header banner")
    is_trending = models.BooleanField(default=False, help_text="Show in trending sidebar")
    is_breaking = models.BooleanField(default=False, help_text="Show in breaking news ticker")
    is_editors_pick = models.BooleanField(default=False, help_text="Show in Editor's Picks section")
    is_top_story = models.BooleanField(default=False, help_text="Show in Top Stories section")
    is_live = models.BooleanField(default=False, help_text="Tick if this is a Live Blog/Live Update article")
    is_web_story = models.BooleanField(default=False, help_text="Tick karein agar is article ko Web Stories (Shorts) mein dikhana hai")
    web_story_created_at = models.DateTimeField(blank=True, null=True, help_text="Story banne ka time (24h expiry ke liye)")
    post_to_facebook = models.BooleanField(default=False, help_text="Tick karein Facebook par post karne ke liye")
    post_to_twitter = models.BooleanField(default=False, help_text="Tick karein Twitter (X) par post karne ke liye")
    post_to_telegram = models.BooleanField(default=False, help_text="Tick karein Telegram channel par post karne ke liye")
    newsletter_sent = models.BooleanField(default=False, help_text="Tick ho jayega jab subscribers ko email bhej diya jayega")
    push_sent = models.BooleanField(default=False, help_text="Tick ho jayega jab push notification bhej diya jayega")

    def save(self, *args, **kwargs):
        # 1. Slug banayein
        if not self.slug:
            self.slug = slugify(self.title)

        # 2. WEB STORY 24-HOUR EXPIRY LOGIC
        if self.is_web_story and not self.web_story_created_at:
            # Jaise hi admin tick karke save karega, current time record ho jayega
            self.web_story_created_at = timezone.now()
        elif not self.is_web_story:
            # Agar admin ne tick hata diya, toh time clear kar do
            self.web_story_created_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            GinIndex(
                SearchVector('title', weight='A', config='english')
                + SearchVector('description', weight='B', config='english')
                + SearchVector('content', weight='C', config='english'),
                name='article_fts_gin_idx',
            ),
        ]

class LiveUpdate(BaseModel):
    """
    Har ek live article ke andar chote-chote updates (jaise cricket commentary ya election count)
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='live_updates')
    title = models.CharField(max_length=255, blank=True, null=True, help_text="Optional short title for this update")
    content = HTMLField(help_text="Update ka content (images, text, embeds)")
    timestamp = models.DateTimeField(default=timezone.now, help_text="Har update ka exact time")
    
    class Meta:
        ordering = ['-timestamp'] # Sabse naya update sabse upar dikhega

    def __str__(self):
        return f"Update for {self.article.title} at {self.timestamp}"
