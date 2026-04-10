from django.contrib.sitemaps import Sitemap
from .models import Article, Category, Author, Tag

class CanonicalSitemap(Sitemap):
    protocol = "https"

class ArticleSitemap(CanonicalSitemap):
    changefreq = "hourly"
    priority = 0.9

    def items(self):
        return Article.objects.filter(status='published').order_by('-published_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        # FIX: Clean URL for articles
        return f"/article/{obj.slug}"

class CategorySitemap(CanonicalSitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        # FIX: Clean URL for categories
        return f"/category/{obj.slug}"

class AuthorSitemap(CanonicalSitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Author.objects.all()

    def location(self, obj):
        return f"/author/{obj.slug}"

class TagSitemap(CanonicalSitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Tag.objects.all()

    def location(self, obj):
        return f"/tag/{obj.slug}"
