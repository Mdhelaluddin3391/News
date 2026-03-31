# news-backend/news/feeds.py
from django.contrib.syndication.views import Feed
from django.conf import settings
from .models import Article

class LatestArticlesFeed(Feed):
    title = "Ferox Times - Latest News"
    link = settings.FRONTEND_URL
    description = "Latest breaking news, trending stories, and in-depth articles from Ferox Times."

    def items(self):
        # Sirf published articles le rahe hain, latest pehle aayenge
        return Article.objects.filter(status='published').order_by('-published_at')[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        # Frontend article page ka direct link
        return f"{settings.FRONTEND_URL}/article?slug={item.slug}"
        
    def item_pubdate(self, item):
        return item.published_at