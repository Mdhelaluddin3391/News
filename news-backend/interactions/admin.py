from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import Bookmark, Comment, NewsletterSubscriber
from news.models import Article
from .models import Poll, PollOption
from .models import Bookmark, Comment, NewsletterSubscriber, Poll, PollOption, PushSubscription  # <-- PushSubscription add karein

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

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; }}
                .container {{ max-width: 650px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
                .header {{ background-color: #1a365d; padding: 25px; text-align: center; color: #ffffff; border-bottom: 5px solid #d32f2f; }}
                .content {{ padding: 30px; color: #333333; }}
                .story {{ padding: 20px; border-radius: 8px; background-color: #f8fafc; border: 1px solid #e2e8f0; margin-bottom: 15px; }}
                .story-title {{ font-size: 18px; color: #1a365d; font-weight: bold; margin: 0 0 10px 0; line-height: 1.4; }}
                .read-more {{ display: inline-block; color: #ffffff; background-color: #d32f2f; padding: 8px 15px; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: bold; margin-top: 5px; }}
                .footer {{ background-color: #f1f5f9; padding: 20px; text-align: center; color: #666666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 26px;">📰 NewsHub</h1>
                    <p style="margin: 5px 0 0 0; font-size: 15px; color: #cbd5e1;">Today's Top Stories</p>
                </div>
                <div class="content">
                    <p style="font-size: 16px; margin-bottom: 25px;">Hello there, <br><br>Here is your daily roundup of the most important stories curated just for you:</p>
        """
        
        # Loop chalakar har article ko HTML blocks mein convert kar rahe hain
        for article in latest_articles:
            article_url = f"{settings.FRONTEND_URL}/article.html?id={article.id}"
            html_content += f"""
                    <div class="story">
                        <h3 class="story-title">{article.title}</h3>
                        <a href="{article_url}" class="read-more" style="color: #ffffff;">Read Full Story &rarr;</a>
                    </div>
            """
            
        html_content += f"""
                </div>
                <div class="footer">
                    Thank you for staying updated with NewsHub!<br><br>
                    Don't want these daily roundups? <a href="{settings.FRONTEND_URL}/unsubscribe.html" style="color: #d32f2f;">Unsubscribe here</a>.
                </div>
            </div>
        </body>
        </html>
        """


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
                html_message=html_content # <--- NAYA PARAMETER
            )
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

# ================== PUSH SUBSCRIPTION ADMIN ==================
@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'endpoint', 'user', 'created_at')
    search_fields = ('endpoint',)