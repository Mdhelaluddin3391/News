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
from django_filters import rest_framework as filters
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.db.models import Q
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django_filters import rest_framework as filters


class ArticleFilter(filters.FilterSet):
    # Relational fields ke liye CharFilter define kar rahe hain
    category__slug = filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    # ⚡ FIX 1: 'author__user__username' ko 'author__user__name' me badal diya
    author__user__name = filters.CharFilter(field_name='author__user__name', lookup_expr='exact')
    tags__slug = filters.CharFilter(field_name='tags__slug', lookup_expr='exact')
    is_breaking = filters.BooleanFilter(method='filter_breaking')
    is_trending = filters.BooleanFilter(method='filter_trending')
    is_featured = filters.BooleanFilter(method='filter_featured')
    is_top_story = filters.BooleanFilter(method='filter_top_story')
    is_web_story = filters.BooleanFilter(method='filter_web_story')

    class Meta:
        model = Article
        # is_editors_pick purely manual hai isliye ise fields me rakha hai
        fields = ['is_editors_pick', 'is_live']

    def filter_breaking(self, queryset, name, value):
        if value:
            # Sirf pichle 12 ghante ki breaking news hi dikhegi
            time_threshold = timezone.now() - timedelta(hours=12)
            return queryset.filter(is_breaking=True, published_at__gte=time_threshold)
        return queryset

    def filter_trending(self, queryset, name, value):
        if value:
            # Trending = (Admin manual tick) YA (Pichle 3 din me 50+ views aaye ho)
            time_threshold = timezone.now() - timedelta(days=3)
            return queryset.filter(
                Q(is_trending=True) | 
                Q(published_at__gte=time_threshold, views__gte=50)
            )
        return queryset

    def filter_featured(self, queryset, name, value):
        if value:
            # Featured = (Admin manual tick) YA (Pichle 2 din ki sabse latest news)
            time_threshold = timezone.now() - timedelta(days=2)
            return queryset.filter(
                Q(is_featured=True) | 
                Q(published_at__gte=time_threshold)
            )
        return queryset

    def filter_top_story(self, queryset, name, value):
        if value:
            # Top Story = (Admin manual tick) YA (Pichle 7 din me 100+ views ho)
            time_threshold = timezone.now() - timedelta(days=7)
            return queryset.filter(
                Q(is_top_story=True) |
                Q(published_at__gte=time_threshold, views__gte=100)
            )
        return queryset

    def filter_web_story(self, queryset, name, value):
        if value:
            time_threshold = timezone.now() - timedelta(hours=24)
            return queryset.filter(is_web_story=True, web_story_created_at__gte=time_threshold)
        return queryset

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Frontend par categories dikhane ke liye (ReadOnly)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug' # Added lookup_field for slug-based routing

    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by('-published_at')
    serializer_class = ArticleSerializer
    lookup_field = 'slug'

    filter_backends = [DjangoFilterBackend]
    filterset_class = ArticleFilter

    @method_decorator(cache_page(60 * 5))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = Article.objects.select_related('category', 'author__user') \
            .prefetch_related('tags') \
            .filter(status='published', published_at__isnull=False)

        # Default Sorting (Latest pehle)
        ordering = ['-published_at']

        # Agar koi Trending ya Top Story filter kar raha hai, toh naturally usey Views ke hisab se SORT bhi karna chahiye
        is_trending = self.request.query_params.get('is_trending') == 'true'
        is_top_story = self.request.query_params.get('is_top_story') == 'true'
        if is_trending or is_top_story:
            ordering = ['-views', '-published_at']

        # Search Logic (Isme koi chedd-chaad nahi ki hai)
        search_term = (self.request.query_params.get('search') or '').strip()
        
        if search_term:
            search_vector = (
                SearchVector('title', weight='A', config='english')
                + SearchVector('tags__name', weight='A', config='english') 
                + SearchVector('category__name', weight='B', config='english')
                + SearchVector('description', weight='B', config='english')
                + SearchVector('author__user__name', weight='C', config='english')
                + SearchVector('content', weight='C', config='english') 
            )
            search_query = SearchQuery(search_term, search_type='websearch', config='english')
            
            return (
                queryset
                .annotate(
                    search=search_vector, 
                    rank=SearchRank(search_vector, search_query)
                )
                .filter(search=search_query)
                .order_by('-rank', '-published_at')
                .distinct()
            )
            
        # Final queryset ko properly order karke bhej rahe hain
        return queryset.order_by(*ordering)
    
    def get_permissions(self):
        # ⚡ [FIX]: Added 'share' here so public users aren't blocked by IsAuthenticated
        if self.action in ['list', 'retrieve', 'increment_view', 'share']:
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def increment_view(self, request, slug=None):
        article = self.get_object()
        article.views += 1
        article.save(update_fields=['views'])
        return Response({'message': 'View count updated', 'views': article.views})
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def share(self, request, slug=None): # Swapped pk for slug
        article = self.get_object()
        
        # Frontend ka actual URL jahan user ko redirect karna hai (Added .html)
        frontend_url = f"{settings.FRONTEND_URL}/article.html?slug={article.slug}"
        
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
            <title>{safe_title} - Ferox Times</title>
            
            <meta property="og:type" content="article">
            <meta property="og:title" content="{safe_title}">
            <meta property="og:description" content="{safe_desc}">
            <meta property="og:image" content="{image_url}">
            <meta property="og:url" content="{frontend_url}">
            <meta property="og:site_name" content="Ferox Times">
            
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
    # ⚡ FIX 3: 'user__username' ko 'user__name' kar diya kyunki User model mein name hai
    lookup_field = 'user__name' 
    lookup_url_kwarg = 'slug'       
    
    # Authors bhi jaldi change nahi hote, isliye 15 minutes cache
    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)