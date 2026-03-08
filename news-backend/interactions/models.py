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
    

class NewsletterSubscriber(BaseModel):
    """Newsletter subscribe karne wale users ke emails"""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True, help_text="False means user ne unsubscribe kar diya hai")

    def __str__(self):
        return self.email