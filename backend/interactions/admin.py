from django.contrib import admin
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

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
    list_display = ('id', 'comment_author', 'reported_by', 'reason', 'comment_preview', 'is_reviewed', 'admin_action', 'created_at')
    list_filter = ('reason', 'is_reviewed', 'admin_action', 'created_at')
    search_fields = ('comment__text', 'comment__user__email', 'reported_by__email', 'description')
    readonly_fields = ('comment', 'reported_by', 'comment_preview', 'comment_author', 'created_at')
    
    fieldsets = (
        ('Report Details', {
            'fields': ('comment', 'comment_author', 'comment_preview', 'reported_by', 'reason', 'description', 'created_at')
        }),
        ('Admin Review', {
            'fields': ('is_reviewed', 'admin_action', 'admin_notes')
        }),
    )
    
    actions = ['mark_reviewed', 'dismiss_reports_action', 'hide_comment_action', 'remove_comment_action', 'warn_user_action']

    def comment_preview(self, obj):
        return obj.comment.text[:80] + "..." if len(obj.comment.text) > 80 else obj.comment.text
    comment_preview.short_description = "Comment"

    def comment_author(self, obj):
        return obj.comment.user.email
    comment_author.short_description = "Comment author"

    def _mark_related_reports(self, report, action, notes):
        CommentReport.objects.filter(comment=report.comment).update(
            is_reviewed=True,
            admin_action=action,
            admin_notes=notes,
        )

    @admin.action(description='✅ Mark as Reviewed')
    def mark_reviewed(self, request, queryset):
        queryset.update(is_reviewed=True)

    @admin.action(description='🟢 Dismiss selected reports')
    def dismiss_reports_action(self, request, queryset):
        queryset.update(is_reviewed=True, admin_action='none')
        self.message_user(request, f"{queryset.count()} reports have been dismissed.")

    @admin.action(description='🚫 Hide comment from the site')
    def hide_comment_action(self, request, queryset):
        for report in queryset:
            report.comment.is_active = False
            report.comment.save(update_fields=['is_active'])
            self._mark_related_reports(report, 'hidden', 'Comment hidden by admin via report interface.')
        self.message_user(request, f"{queryset.count()} comments have been hidden.")

    @admin.action(description='🗑️ Remove comment from public view')
    def remove_comment_action(self, request, queryset):
        for report in queryset:
            report.comment.is_active = False
            report.comment.save(update_fields=['is_active'])
            self._mark_related_reports(report, 'deleted', 'Comment removed from public view by admin.')
        self.message_user(request, f"{queryset.count()} comments have been removed from public view.")

    @admin.action(description='⚠️ Warn User & Mark Actioned')
    def warn_user_action(self, request, queryset):
        for report in queryset:
            self._mark_related_reports(report, 'warn_user', 'Comment author flagged for moderator warning.')
        self.message_user(request, f"{queryset.count()} comment authors have been flagged for warning.")

    def save_model(self, request, obj, form, change):
        if obj.admin_action in ['hidden', 'deleted']:
            obj.comment.is_active = False
            obj.comment.save(update_fields=['is_active'])
        obj.is_reviewed = True if obj.admin_action != 'none' else obj.is_reviewed
        super().save_model(request, obj, form, change)

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

        subject = "📰 Today's Top Stories from Ferox Times"
        message = "Hello!\n\nHere are the latest top stories for you:\n\n"
        html_content = f"<html><body><h2>📰 Ferox Times Top Stories</h2><p>Hello!</p>"
        
        for article in latest_articles:
            article_url = f"{settings.FRONTEND_URL}/article?slug={article.slug}"
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
