from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Article, Category
from .serializers import ArticleSerializer, CategorySerializer
from users.permissions import IsReporterAuthorOrAbove, IsOwnerOrEditorOrAdmin

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Frontend par categories dikhane ke liye (ReadOnly)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by('-published_at')
    serializer_class = ArticleSerializer
    
    # 🔴 YAHAN FILTERING ADD KI GAYI HAI 🔴
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # Ye fields frontend se bheje gaye URLs ko handle karengi (e.g. ?category__slug=tech)
    filterset_fields = ['category__slug', 'author', 'is_featured', 'is_trending', 'is_breaking']
    
    # Ye search.html ke liye kaam aayega (e.g. ?search=query)
    search_fields = ['title', 'content', 'description']
    
    def get_permissions(self):
        # Anyone can read published articles
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        
        # Only authors, reporters, editors, and admins can create
        elif self.action == 'create':
            permission_classes = [IsReporterAuthorOrAbove]
        
        # For edit/delete, check object ownership or if they are an editor/admin
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrEditorOrAdmin]
            
        else:
            permission_classes = [permissions.IsAuthenticated]
            
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        # Automatically set the author to the logged-in user when creating an article
        # Assuming you link the Article to the Author profile
        serializer.save(author=self.request.user.author_profile)