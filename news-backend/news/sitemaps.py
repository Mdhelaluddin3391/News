# news-backend/news/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.conf import settings
from .models import Article, Category

class ArticleSitemap(Sitemap):
    changefreq = "hourly"
    priority = 0.9

    def items(self):
        return Article.objects.filter(status='published').order_by('-published_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        # Frontend article page ka URL
        return f"{settings.FRONTEND_URL}/article.html?id={obj.id}"

class CategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        # Frontend category page ka URL
        return f"{settings.FRONTEND_URL}/index.html?category={obj.slug}"