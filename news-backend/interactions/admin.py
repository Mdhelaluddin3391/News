from django.contrib import admin
from .models import Bookmark, Comment

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'created_at')
    list_filter = ('created_at',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('text',)