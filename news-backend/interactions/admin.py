from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import Bookmark, Comment, NewsletterSubscriber
from news.models import Article
from .models import Poll, PollOption


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at')
    list_filter = ('created_at',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('text',)



@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email',)
    
    # NAYA: Custom Action ko yahan register karein
    actions = ['send_latest_news_email']

    # ================== NAYA CUSTOM ADMIN ACTION ==================
    @admin.action(description='📧 Send Latest News to Selected Subscribers')
    def send_latest_news_email(self, request, queryset):
        # 1. Sirf 'Active' subscribers ko filter karein (jin hone unsubscribe nahi kiya hai)
        active_subscribers = queryset.filter(is_active=True)
        
        if not active_subscribers.exists():
            self.message_user(request, "Error: Koi active subscriber select nahi kiya gaya.", level='error')
            return

        # 2. Database se latest 3 "Published" articles nikalein
        latest_articles = Article.objects.filter(status='published').order_by('-published_at')[:3]
        
        if not latest_articles.exists():
            self.message_user(request, "Error: Bhejne ke liye koi published article nahi mila.", level='error')
            return

        # 3. Email ka Subject aur Message (Body) taiyaar karein
        subject = "📰 Today's Top Stories from NewsHub"
        message = "Hello!\n\nHere are the latest top stories for you:\n\n"
        
        for article in latest_articles:
            # Har article ka URL banayein taaki user click karke padh sake
            article_url = f"{settings.FRONTEND_URL}/article.html?id={article.id}"
            message += f"📌 {article.title}\nRead full article: {article_url}\n\n"
            
        message += "Thank you for subscribing to NewsHub!\n"
        message += f"To unsubscribe, visit: {settings.FRONTEND_URL}/unsubscribe.html"

        # 4. Sabhi active subscribers ke emails ki list banayein
        recipient_list = [sub.email for sub in active_subscribers]

        # 5. Email bhejein!
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            # Success message admin panel par dikhayein
            self.message_user(request, f"✅ Newsletter successfully sent to {active_subscribers.count()} subscribers!")
        except Exception as e:
            self.message_user(request, f"❌ Error sending email: {str(e)}", level='error')


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 2 # Ek baar mein 2 option box dikhenge

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_active', 'created_at')
    list_editable = ('is_active',)
    inlines = [PollOptionInline]