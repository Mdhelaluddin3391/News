from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet, CategoryViewSet
from .views import ArticleViewSet, CategoryViewSet, AuthorViewSet

router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'authors', AuthorViewSet, basename='author')

urlpatterns = [
    path('', include(router.urls)),
]