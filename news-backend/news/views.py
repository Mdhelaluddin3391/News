from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

# NAYE IMPORTS CACHING KE LIYE ⚡
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import Article, Category, Author
from .serializers import ArticleSerializer, CategorySerializer, AuthorSerializer
from users.permissions import IsReporterAuthorOrAbove, IsOwnerOrEditorOrAdmin

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Frontend par categories dikhane ke liye (ReadOnly)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    # Categories jaldi change nahi hoti, isliye 15 minute (60 * 15 seconds) tak cache karenge
    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by('-published_at')
    serializer_class = ArticleSerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # 'is_editors_pick' aur 'tags__slug' yahan filter mein hain
    filterset_fields = ['category__slug', 'author', 'is_featured', 'is_trending', 'is_breaking', 'is_editors_pick', 'tags__slug']
    search_fields = ['title', 'content', 'description']
    
    def get_permissions(self):
        # Yahan 'increment_view' add kiya gaya hai taaki public access ho
        if self.action in ['list', 'retrieve', 'increment_view']:
            permission_classes = [permissions.AllowAny]
        
        elif self.action == 'create':
            permission_classes = [IsReporterAuthorOrAbove]
        
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrEditorOrAdmin]
            
        else:
            permission_classes = [permissions.IsAuthenticated]
            
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.author_profile)

    # ⚡ Sirf List (Sabhi articles) aur Retrieve (Single article) ko cache karenge 5 minute ke liye
    @method_decorator(cache_page(60 * 5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 5))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # Naya Endpoint: Views badhane ke liye
    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def increment_view(self, request, pk=None):
        article = self.get_object()
        article.views += 1
        article.save(update_fields=['views'])
        return Response({'message': 'View count updated', 'views': article.views})

class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """Frontend par sabhi authors ki list dikhane ke liye (ReadOnly)"""
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]
    
    # Authors bhi jaldi change nahi hote, isliye 15 minutes cache
    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)