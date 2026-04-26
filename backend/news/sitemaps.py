from django.contrib.sitemaps import Sitemap
from django.utils import timezone
from .models import Article, Category, Author, Tag


# ── Base class: enforce https protocol ────────────────────────────────────────
class CanonicalSitemap(Sitemap):
    protocol = "https"


# ── 1. ARTICLES ───────────────────────────────────────────────────────────────
# Priority: Highest (0.9). Crawl hourly — primary indexable content.
class ArticleSitemap(CanonicalSitemap):
    changefreq = "hourly"
    priority = 0.9
    limit = 50000  # Google's sitemap limit

    def items(self):
        return (
            Article.objects
            .filter(status='published', published_at__isnull=False)
            .only('slug', 'updated_at', 'published_at')
            .order_by('-published_at')
        )

    def lastmod(self, obj):
        return obj.updated_at or obj.published_at

    def location(self, obj):
        return f"/article/{obj.slug}"


# ── 2. CATEGORIES ─────────────────────────────────────────────────────────────
# Priority: 0.8. Updated daily as new articles are added.
class CategorySitemap(CanonicalSitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        # Only include categories that have at least one published article
        return (
            Category.objects
            .filter(articles__status='published')
            .distinct()
            .only('slug')
        )

    def lastmod(self, obj):
        # Use the most recently published article in this category
        latest = (
            obj.articles
            .filter(status='published')
            .order_by('-published_at')
            .values_list('updated_at', flat=True)
            .first()
        )
        return latest or timezone.now()

    def location(self, obj):
        return f"/category/{obj.slug}"


# ── 3. AUTHORS ────────────────────────────────────────────────────────────────
# Priority: 0.6. Authors who have at least one published article.
class AuthorSitemap(CanonicalSitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        # Only include authors with at least one published article
        return (
            Author.objects
            .filter(articles__status='published')
            .distinct()
            .only('slug')
        )

    def lastmod(self, obj):
        latest = (
            obj.articles
            .filter(status='published')
            .order_by('-published_at')
            .values_list('updated_at', flat=True)
            .first()
        )
        return latest or timezone.now()

    def location(self, obj):
        return f"/author/{obj.slug}"


# ── 4. TAGS ───────────────────────────────────────────────────────────────────
# Priority: 0.5. Tags that have at least one published article.
class TagSitemap(CanonicalSitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        # Only include tags that have at least one published article
        return (
            Tag.objects
            .filter(articles__status='published')
            .distinct()
            .only('slug')
        )

    def lastmod(self, obj):
        latest = (
            obj.articles
            .filter(status='published')
            .order_by('-published_at')
            .values_list('updated_at', flat=True)
            .first()
        )
        return latest or timezone.now()

    def location(self, obj):
        return f"/tag/{obj.slug}"


# ── 5. STATIC PAGES ───────────────────────────────────────────────────────────
# Homepage, About, Contact, Careers, etc. — editorial landing pages.
class StaticPageSitemap(CanonicalSitemap):
    changefreq = "monthly"

    # (url_path, priority, changefreq)
    _pages = [
        ("/", 1.0, "daily"),
        ("/about", 0.7, "monthly"),
        ("/contact", 0.6, "monthly"),
        ("/privacy", 0.4, "yearly"),
        ("/terms", 0.4, "yearly"),
        ("/cookie-policy", 0.4, "yearly"),
        ("/editorial-guidelines", 0.5, "monthly"),
        ("/faq", 0.5, "monthly"),
        ("/careers", 0.5, "monthly"),
        ("/advertise", 0.5, "monthly"),
    ]

    def items(self):
        return self._pages

    def location(self, item):
        return item[0]

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]

    def lastmod(self, item):
        return timezone.now().replace(microsecond=0)
