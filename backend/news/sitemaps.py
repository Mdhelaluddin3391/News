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
        return f"{settings.FRONTEND_URL}/article.html?id={obj.id}"

class CategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return f"{settings.FRONTEND_URL}/index.html?category={obj.slug}"

class AuthorSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Author.objects.all()

    def location(self, obj):
        return f"{settings.FRONTEND_URL}/author.html?id={obj.id}"

class TagSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Tag.objects.all()

    def location(self, obj):
        return f"{settings.FRONTEND_URL}/tag.html?slug={obj.slug}&name={obj.name}"

class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return ['about.html', 'contact.html', 'careers.html', 'advertise.html', 'authors.html']

    def location(self, item):
        return f"{settings.FRONTEND_URL}/{item}"