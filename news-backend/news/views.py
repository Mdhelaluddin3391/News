from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Article, Category
from .serializers import ArticleSerializer, CategorySerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Frontend par categories dikhane ke liye (ReadOnly)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """Articles ko list aur retrieve karne ke liye"""
    queryset = Article.objects.filter(status='published').order_by('-published_at')
    serializer_class = ArticleSerializer
    permission_classes = [permissions.AllowAny]
    
    # Filtering aur Searching add kar rahe hain
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'is_featured', 'is_trending', 'is_breaking']
    search_fields = ['title', 'description', 'content']
    ordering_fields = ['published_at', 'views']

    def retrieve(self, request, *args, **kwargs):
        # Jab koi article read kare, toh views count badha dein
        instance = self.get_object()
        instance.views += 1
        instance.save()
        return super().retrieve(request, *args, **kwargs)