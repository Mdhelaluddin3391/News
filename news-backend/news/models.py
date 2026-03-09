import os
import sys
from io import BytesIO
from PIL import Image
from django.db import models
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.text import slugify
from tinymce.models import HTMLField
from core.models import BaseModel
from users.models import User

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

    def save(self, *args, **kwargs):
        # 1. Slug banayein
        if not self.slug:
            self.slug = slugify(self.title)
            
        # 2. Image Compression & WebP Conversion
        if self.featured_image:
            # Check karein ki image pehle se webp toh nahi hai
            if not self.featured_image.name.lower().endswith('.webp'):
                # Image ko open karein
                img = Image.open(self.featured_image)
                
                # Agar image PNG (RGBA) hai, toh usko RGB mein convert karein (WebP support ke liye)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                    
                # Resize karein (Agar image bahut badi hai toh max width 1200px set karein)
                img.thumbnail((1200, 800), Image.Resampling.LANCZOS)
                
                # Image ko memory mein save karein WebP format mein
                output = BytesIO()
                img.save(output, format='WEBP', quality=80) # Quality 80 means good quality, low size
                output.seek(0)
                
                # Puraana extension hata kar .webp lagayein
                file_name = os.path.splitext(self.featured_image.name)[0] + '.webp'
                
                # Nayi compressed file ko save karne ke liye ready karein
                self.featured_image = InMemoryUploadedFile(
                    output, 'ImageField', file_name, 'image/webp',
                    sys.getsizeof(output), None
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
