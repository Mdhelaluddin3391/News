from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import Http404
from django.http import HttpResponse
from django.conf import settings
from django.utils.html import escape
from django.utils import timezone
from datetime import timedelta
from .models import Article, Category, Author
from .serializers import ArticleSerializer, CategorySerializer, AuthorSerializer
from users.permissions import IsReporterAuthorOrAbove, IsOwnerOrEditorOrAdmin
from django_filters import rest_framework as filters
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from django.db.models import F, Q
from rest_framework.throttling import AnonRateThrottle
from django.shortcuts import render

class ArticleViewThrottle(AnonRateThrottle):
    rate = '10/day'

class ArticleFilter(filters.FilterSet):
    category__slug = filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    author__slug = filters.CharFilter(field_name='author__slug', lookup_expr='exact')
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
            time_threshold = timezone.now() - timedelta(hours=12)
            return queryset.filter(is_breaking=True, published_at__gte=time_threshold)
        return queryset

    def filter_trending(self, queryset, name, value):
        if value:
            time_threshold = timezone.now() - timedelta(days=3)
            return queryset.filter(
                Q(is_trending=True) | 
                Q(published_at__gte=time_threshold, views__gte=50)
            )
        return queryset

    def filter_featured(self, queryset, name, value):
        if value:
            time_threshold = timezone.now() - timedelta(days=2)
            return queryset.filter(
                Q(is_featured=True) | 
                Q(published_at__gte=time_threshold)
            )
        return queryset

    def filter_top_story(self, queryset, name, value):
        if value:
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
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by('-published_at')
    serializer_class = ArticleSerializer
    lookup_field = 'slug'

    filter_backends = [DjangoFilterBackend]
    filterset_class = ArticleFilter
    
    def get_queryset(self):
        queryset = Article.objects.select_related('category', 'author__user').prefetch_related('tags', 'live_updates')

        if self.action in ['list', 'retrieve', 'increment_view', 'share'] and not self.request.user.is_staff:
            queryset = queryset.filter(status='published', published_at__isnull=False)
        elif not self.request.user.is_staff and self.request.user.is_authenticated:
            queryset = queryset.filter(Q(author__user=self.request.user) | Q(status='published', published_at__isnull=False))

        ordering = ['-published_at']

        is_trending = self.request.query_params.get('is_trending') == 'true'
        is_top_story = self.request.query_params.get('is_top_story') == 'true'
        if is_trending or is_top_story:
            ordering = ['-views', '-published_at']

        search_term = (self.request.query_params.get('search') or '').strip()
        
        if search_term:
            if connection.vendor != 'postgresql':
                return (
                    queryset.filter(
                        Q(title__icontains=search_term)
                        | Q(description__icontains=search_term)
                        | Q(content__icontains=search_term)
                        | Q(category__name__icontains=search_term)
                        | Q(tags__name__icontains=search_term)
                        | Q(author__user__name__icontains=search_term)
                        | Q(author__slug__icontains=search_term)
                    )
                    .order_by('-published_at')
                    .distinct()
                )

            search_vector = (
                SearchVector('title', weight='A', config='english')
                + SearchVector('tags__name', weight='A', config='english') 
                + SearchVector('category__name', weight='B', config='english')
                + SearchVector('description', weight='B', config='english')
                + SearchVector('author__slug', weight='C', config='english')
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
            
        return queryset.order_by(*ordering)
    
    def get_permissions(self):
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
        author_profile, _ = Author.objects.get_or_create(
            user=self.request.user,
            defaults={'role': self.request.user.get_role_display()},
        )
        
        # Security: Activist/Guest Writers (authors) cannot publish articles directly.
        # Force status to draft if role is 'author' or 'reporter' unless they are staff/superuser.
        if self.request.user.role in ['author', 'reporter'] and not self.request.user.is_staff:
            serializer.save(author=author_profile, status='draft', is_imported=False)
        else:
            serializer.save(author=author_profile)

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)

        if lookup_value and str(lookup_value).isdigit():
            queryset = self.filter_queryset(self.get_queryset())
            obj = queryset.filter(slug=lookup_value).first()
            if obj is None:
                obj = queryset.filter(pk=int(lookup_value)).first()
            if obj is None:
                raise Http404
            self.check_object_permissions(self.request, obj)
            return obj

        return super().get_object()

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny], throttle_classes=[ArticleViewThrottle])
    def increment_view(self, request, slug=None):
        article = self.get_object()
        Article.objects.filter(pk=article.pk).update(views=F('views') + 1)
        article.refresh_from_db(fields=['views'])
        return Response({'message': 'View count updated', 'views': article.views})
    

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def share(self, request, slug=None):
        article = self.get_object()
        image_url = f"{settings.FRONTEND_URL}/images/default-news.png"
        if article.featured_image:
            image_path = article.featured_image.url
            if image_path.startswith(('http://', 'https://')):
                image_url = image_path
            else:
                image_url = f"{settings.FRONTEND_URL.rstrip('/')}{image_path}"
        
        # IMPROVEMENT: Using Django render instead of hardcoded HTML string to prevent XSS
        context = {
            'safe_title': article.title,
            'safe_desc': article.description[:200] if article.description else "",
            'frontend_url': f"{settings.FRONTEND_URL}/article/{article.slug}",
            'image_url': image_url,
        }
        
        return render(request, 'news/share_redirect.html', context)

class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
