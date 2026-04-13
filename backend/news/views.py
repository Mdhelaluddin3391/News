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
from functools import reduce
from operator import and_

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
        """
        Trending Logic:
        - is_trending=True → Admin override ya Celery auto-flagged (100+ views in 3 days)
        - is_trending=True articles hamesha show hote hain (admin override protection)
        - View-threshold wale fresh articles bhi trending mein aa sakte hain agar flag set nahi hua
        """
        if value:
            time_threshold = timezone.now() - timedelta(days=3)
            return queryset.filter(
                Q(is_trending=True) |
                Q(published_at__gte=time_threshold, views__gte=100)
            ).order_by('-views', '-published_at')  # Most views first
        return queryset

    def filter_featured(self, queryset, name, value):
        """
        Featured Logic:
        - is_featured=True (admin override OR auto-flagged by Celery task) → always show
        - Last 48 hours ke published articles bhi featured mein aate hain (rolling window)
        """
        if value:
            time_threshold = timezone.now() - timedelta(hours=48)  # 2-day rolling window
            return queryset.filter(
                Q(is_featured=True) |
                Q(published_at__gte=time_threshold)
            ).order_by('-published_at')  # Newest first in featured
        return queryset

    def filter_top_story(self, queryset, name, value):
        """
        Top Story Logic:
        - is_top_story=True (pure manual admin setting) → hamesha dikhega
        - Last 7 din mein 200+ views wale articles bhi top story mein aate hain
        """
        if value:
            time_threshold = timezone.now() - timedelta(days=7)
            return queryset.filter(
                Q(is_top_story=True) |
                Q(published_at__gte=time_threshold, views__gte=200)
            ).order_by('-views', '-published_at')
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
            words = search_term.split()
            
            if connection.vendor != 'postgresql':
                q_objects = []
                for word in words:
                    q_objects.append(
                        Q(title__icontains=word)
                        | Q(description__icontains=word)
                        | Q(content__icontains=word)
                        | Q(category__name__icontains=word)
                        | Q(tags__name__icontains=word)
                        | Q(author__user__name__icontains=word)
                        | Q(author__slug__icontains=word)
                    )
                query = reduce(and_, q_objects)
                return queryset.filter(query).order_by('-published_at').distinct()

            pg_query_string = " & ".join(f"{word}:*" for word in words)
            search_query_raw = SearchQuery(pg_query_string, search_type='raw', config='english')
            search_query_web = SearchQuery(search_term, search_type='websearch', config='english')

            search_vector = (
                SearchVector('title', weight='A', config='english')
                + SearchVector('tags__name', weight='A', config='english') 
                + SearchVector('category__name', weight='B', config='english')
                + SearchVector('author__user__name', weight='B', config='english')
                + SearchVector('description', weight='C', config='english')
                + SearchVector('content', weight='D', config='english') 
            )
            
            icontains_q_objects = []
            for word in words:
                icontains_q_objects.append(
                    Q(title__icontains=word)
                    | Q(tags__name__icontains=word)
                    | Q(author__user__name__icontains=word)
                    | Q(category__name__icontains=word)
                )
            icontains_query = reduce(and_, icontains_q_objects)

            return (
                queryset
                .annotate(
                    search=search_vector, 
                    rank=SearchRank(search_vector, search_query_raw)
                )
                .filter(Q(search=search_query_raw) | Q(search=search_query_web) | icontains_query)
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
