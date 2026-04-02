from django.contrib.sitemaps import Sitemap
from django.conf import settings
from .models import Article, Category, Author, Tag

class ArticleSitemap(Sitemap):
    changefreq = "hourly"
    priority = 0.9

    def items(self):
        return Article.objects.filter(status='published').order_by('-published_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        # FIX: Clean URL for articles
        return f"/article/{obj.slug}"

class CategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        # FIX: Clean URL for categories
        return f"/category/{obj.slug}"

class AuthorSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Author.objects.all()

    def location(self, obj):
        # FIX: Clean URL for authors
        slug = obj.user.username if hasattr(obj.user, 'username') else obj.id
        return f"/author/{slug}"

class TagSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Tag.objects.all()

    def location(self, obj):
        # FIX: Clean URL for tags
        return f"/tag/{obj.slug}"

class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        # FIX: Use clean URLs for static views
        return ['about', 'contact', 'careers', 'advertise', 'authors']

    def location(self, item):
        return f"/{item}"
