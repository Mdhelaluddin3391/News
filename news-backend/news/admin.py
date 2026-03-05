from django.contrib import admin
from .models import Category, Author, Article

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'status', 'published_at', 'views')
    list_filter = ('status', 'category', 'is_featured', 'is_trending')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}