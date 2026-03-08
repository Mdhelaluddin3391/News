from django.contrib import admin
# Naya model NewsletterSubscriber import kiya gaya hai
from .models import Bookmark, Comment, NewsletterSubscriber

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at')
    list_filter = ('created_at',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('text',)

# --- NAYA CODE YAHAN SE START HAI ---
@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    # Admin panel mein ye columns dikhenge
    list_display = ('email', 'is_active', 'created_at')
    
    # Right side mein filter karne ka option aayega (active/inactive ya date ke hisaab se)
    list_filter = ('is_active', 'created_at')
    
    # Upar ek search bar aayega jisme email type karke search kar sakte hain
    search_fields = ('email',)
# --- NAYA CODE YAHAN END HAI ---