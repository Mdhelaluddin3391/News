from django.contrib import admin
from django.core.mail import EmailMultiAlternatives # NAYA: Secure email ke liye
from django.conf import settings
from news.models import Article
from .models import Bookmark, Comment, CommentReport, NewsletterSubscriber, Poll, PollOption, PushSubscription

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'article__title')
    autocomplete_fields = ['user', 'article'] # NAYA: Searchable dropdowns for large data

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'short_text', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('text', 'user__email', 'user__name', 'article__title')
    list_editable = ('is_active',)
    actions = ['approve_comments', 'hide_comments']

    def short_text(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    short_text.short_description = "Comment"

    @admin.action(description='✅ Approve (Show) selected comments')
    def approve_comments(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='🚫 Hide (Moderate) selected comments')
    def hide_comments(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(CommentReport)
class CommentReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reported_by', 'reason', 'comment_preview', 'is_reviewed', 'admin_action', 'created_at')
    list_filter = ('reason', 'is_reviewed', 'admin_action', 'created_at')
    search_fields = ('comment__text', 'reported_by__email', 'description')
    readonly_fields = ('comment', 'reported_by', 'created_at')
    
    fieldsets = (
        ('Report Details', {
            'fields': ('comment', 'reported_by', 'reason', 'description', 'created_at')
        }),
        ('Admin Review', {
            'fields': ('is_reviewed', 'admin_action', 'admin_notes')
        }),
    )
    
    actions = ['mark_reviewed', 'hide_comment_action', 'delete_comment_action', 'warn_user_action']

    def comment_preview(self, obj):
        text = obj.comment.text[:50] + "..." if len(obj.comment.text) > 50 else obj.comment.text
        return text
    comment_preview.short_description = "Comment"

    @admin.action(description='✅ Mark as Reviewed')
    def mark_reviewed(self, request, queryset):
        queryset.update(is_reviewed=True)

    @admin.action(description='🚫 Hide Comment & Mark No Action')
    def hide_comment_action(self, request, queryset):
        for report in queryset:
            report.comment.is_active = False
            report.comment.save()
            report.is_reviewed = True
            report.admin_action = 'hidden'
            report.admin_notes = 'Comment hidden by admin via report interface'
            report.save()
        self.message_user(request, f"{queryset.count()} comments have been hidden.")

    @admin.action(description='🗑️ Delete Comment & Mark Deleted')
    def delete_comment_action(self, request, queryset):
        for report in queryset:
            comment_id = report.comment.id
            report.comment.delete()
            report.is_reviewed = True
            report.admin_action = 'deleted'
            report.admin_notes = 'Comment deleted by admin via report interface'
            report.save()
        self.message_user(request, f"{queryset.count()} comments have been deleted.")

    @admin.action(description='⚠️ Warn User & Mark Actioned')
    def warn_user_action(self, request, queryset):
        for report in queryset:
            user_email = report.reported_by.email
            # Future: Send warning email to user
            report.is_reviewed = True
            report.admin_action = 'warn_user'
            report.admin_notes = 'User warned about report'
            report.save()
        self.message_user(request, f"{queryset.count()} users have been warned.")

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email',)
    actions = ['send_latest_news_email', 'activate_subscribers', 'deactivate_subscribers']

    @admin.action(description='🟢 Mark as Active')
    def activate_subscribers(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='🔴 Mark as Inactive')
    def deactivate_subscribers(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description='📧 Send Latest News to Selected Subscribers (BCC Secure)')
    def send_latest_news_email(self, request, queryset):
        active_subscribers = queryset.filter(is_active=True)
        if not active_subscribers.exists():
            self.message_user(request, "Error: Koi active subscriber select nahi kiya gaya.", level='error')
            return

        latest_articles = Article.objects.filter(status='published').order_by('-published_at')[:3]
        if not latest_articles.exists():
            self.message_user(request, "Error: Bhejne ke liye koi published article nahi mila.", level='error')
            return

        subject = "📰 Today's Top Stories from Forex Times"
        message = "Hello!\n\nHere are the latest top stories for you:\n\n"
        html_content = f"<html><body><h2>📰 Forex Times Top Stories</h2><p>Hello!</p>"
        
        for article in latest_articles:
            article_url = f"{settings.FRONTEND_URL}/article.html?id={article.id}"
            message += f"📌 {article.title}\n{article_url}\n\n"
            html_content += f"<h3>{article.title}</h3><a href='{article_url}'>Read More</a><br><br>"
            
        html_content += f"<hr><p><a href='{settings.FRONTEND_URL}/unsubscribe.html'>Unsubscribe</a></p></body></html>"

        recipient_list = list(active_subscribers.values_list('email', flat=True))

        try:
            # NAYA: BCC ka use privacy ke liye
            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.DEFAULT_FROM_EMAIL], # Apna hi no-reply daalein
                bcc=recipient_list                # Saare users yahan aayenge
            )
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send(fail_silently=False)
            
            self.message_user(request, f"✅ Newsletter securely sent to {len(recipient_list)} subscribers!")
        except Exception as e:
            self.message_user(request, f"❌ Error sending email: {str(e)}", level='error')


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 2

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('question',)
    inlines = [PollOptionInline]

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'endpoint', 'user', 'created_at')
    search_fields = ('endpoint', 'user__email')