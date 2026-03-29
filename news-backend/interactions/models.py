from django.db import models
from core.models import BaseModel
from users.models import User
from news.models import Article

class Bookmark(BaseModel):
    """User ke saved articles ke liye (saved.js)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='bookmarked_by')

    class Meta:
        # Ek user ek article ko ek hi baar save kar sake
        unique_together = ('user', 'article')

    def __str__(self):
        return f"{self.user.name} saved {self.article.title}"

class Comment(BaseModel):
    """Article par users ke comments (comments.js)"""
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    
    # Moderation ke liye flag (kisi ne gali likhi ho toh admin hide kar sake)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Comment by {self.user.name} on {self.article.title}"

class CommentReport(BaseModel):
    """Comments jo offensive hain unhe report karne ke liye"""
    REASON_CHOICES = (
        ('spam', 'Spam'),
        ('offensive', 'Offensive Language'),
        ('inappropriate', 'Inappropriate Content'),
        ('harassment', 'Harassment'),
        ('false_info', 'False Information'),
        ('other', 'Other'),
    )
    
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_comments')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True, null=True, help_text="Additional details about the report")
    
    # Status tracking
    is_reviewed = models.BooleanField(default=False, help_text="Admin review ho gaya ya nahi")
    admin_action = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Action'),
            ('hidden', 'Comment Hidden'),
            ('deleted', 'Comment Deleted'),
            ('warn_user', 'User Warned'),
        ],
        default='none',
        help_text="Admin ka action"
    )
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin ke notes")
    
    class Meta:
        # Ek user ek comment ko sirf ek baar report kar sake
        unique_together = ('comment', 'reported_by')

    def __str__(self):
        return f"Report: {self.get_reason_display()} - {self.comment.id}"
    


class NewsletterSubscriber(BaseModel):
    """Newsletter subscribe karne wale users ke emails"""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True, help_text="False means user ne unsubscribe kar diya hai")
    
    # Token tracking fields for unsubscribe security
    unsubscribe_token = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Current unsubscribe token issued to user"
    )
    unsubscribe_token_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the unsubscribe token was used (one-time use)"
    )

    def __str__(self):
        return self.email
    
class Poll(BaseModel):
    """Admin dwara banaye gaye polls/surveys"""
    question = models.CharField(max_length=255, help_text="Poll ka sawal likhein")
    description = models.TextField(blank=True, null=True, help_text="Thoda context ya description poll ke liye (Optional)")
    is_active = models.BooleanField(default=False, help_text="Keval ek poll ko active rakhein jo frontend par dikhega")

    def __str__(self):
        return self.question

class PollOption(BaseModel):
    """Poll ke options (e.g., Option A, Option B)"""
    poll = models.ForeignKey(Poll, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=255, help_text="Option ka naam")
    votes = models.IntegerField(default=0, help_text="Total votes received")

    def __str__(self):
        return f"{self.text} ({self.votes} votes)"
    
class PushSubscription(BaseModel):
    """Users ke browser ki push notification subscription details"""
    endpoint = models.URLField(max_length=500, unique=True)
    auth = models.CharField(max_length=100)
    p256dh = models.CharField(max_length=100)
    # Optional: Agar user logged in hai toh usko link kar sakte hain
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Push Sub - {self.id}"