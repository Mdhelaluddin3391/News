from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.conf import settings
from django.utils.html import escape
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone
from datetime import timedelta
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
    
    filter_backends = [DjangoFilterBackend]
    
    # 'is_editors_pick' aur 'tags__slug' yahan filter mein hain
    filterset_fields = ['category__slug', 'author', 'is_featured', 'is_trending', 'is_breaking', 'is_editors_pick', 'tags__slug', 'is_top_story', 'is_web_story']

    def get_queryset(self):
        queryset = Article.objects.select_related('category', 'author__user').prefetch_related('tags').order_by('-published_at')
        
        # --- 24 HOURS STORY EXPIRY LOGIC ---
        is_web_story = self.request.query_params.get('is_web_story')
        if is_web_story == 'true':
            # Current time se exactly 24 ghante (24 hours) piche ka time nikalein
            time_threshold = timezone.now() - timedelta(hours=24)
            # Sirf wahi stories filter karein jinka time threshold se bada (nyaya) ho
            queryset = queryset.filter(is_web_story=True, web_story_created_at__gte=time_threshold)

        search_term = (self.request.query_params.get('search') or '').strip()
        if search_term:
            search_vector = (
                SearchVector('title', weight='A', config='english')
                + SearchVector('description', weight='B', config='english')
                + SearchVector('content', weight='C', config='english')
                + SearchVector('category__name', weight='B', config='english')
                + SearchVector('author__user__name', weight='B', config='english')
            )
            search_query = SearchQuery(search_term, search_type='websearch', config='english')
            queryset = (
                queryset
                .annotate(search=search_vector, rank=SearchRank(search_vector, search_query))
                .filter(search=search_query)
                .order_by('-rank', '-published_at')
                .distinct()
            )
            
        return queryset
    
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
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def share(self, request, pk=None):
        article = self.get_object()
        
        # Frontend ka actual URL jahan user ko redirect karna hai
        frontend_url = f"{settings.FRONTEND_URL}/article.html?id={article.id}"
        
        # Article ki Image (Agar nahi hai toh default lagayein)
        if article.featured_image:
            image_url = request.build_absolute_uri(article.featured_image.url)
        else:
            image_url = ""
        
        # Safe Text
        safe_title = escape(article.title)
        safe_desc = escape(article.description[:200]) if article.description else ""

        # Facebook, WhatsApp aur Twitter ko jo HTML format samajh aata hai
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{safe_title} - Forex Times</title>
            
            <meta property="og:type" content="article">
            <meta property="og:title" content="{safe_title}">
            <meta property="og:description" content="{safe_desc}">
            <meta property="og:image" content="{image_url}">
            <meta property="og:url" content="{frontend_url}">
            <meta property="og:site_name" content="Forex Times">
            
            <meta name="twitter:card" content="summary_large_image">
            <meta name="twitter:title" content="{safe_title}">
            <meta name="twitter:description" content="{safe_desc}">
            <meta name="twitter:image" content="{image_url}">
            
            <meta http-equiv="refresh" content="0; url={frontend_url}">
            <script>window.location.href = "{frontend_url}";</script>
        </head>
        <body>
            <p>Redirecting to article... <a href="{frontend_url}">Click here</a> if not redirected automatically.</p>
        </body>
        </html>
        """
        return HttpResponse(html_content)

class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """Frontend par sabhi authors ki list dikhane ke liye (ReadOnly)"""
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]
    
    # Authors bhi jaldi change nahi hote, isliye 15 minutes cache
    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
