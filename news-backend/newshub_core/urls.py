"""
URL configuration for newshub_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import status
from rest_framework.response import Response
from interactions.views import SubscribeNewsletterView, UnsubscribeNewsletterView
from core.views import ContactMessageCreateView
from django.contrib.sitemaps.views import sitemap
from news.sitemaps import ArticleSitemap, CategorySitemap
from news.feeds import LatestArticlesFeed
from core.views import ContactMessageCreateView, SiteSettingAPIView
from django.utils.decorators import method_decorator
from rest_framework.throttling import ScopedRateThrottle
from news.sitemaps import ArticleSitemap, CategorySitemap, AuthorSitemap, TagSitemap, StaticViewSitemap
from django.contrib.auth import get_user_model

User = get_user_model()



sitemaps = {
    'articles': ArticleSitemap,
    'categories': CategorySitemap,
    'authors': AuthorSitemap,
    'tags': TagSitemap,
    'static': StaticViewSitemap,
}

class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        """Override to check if user has verified their email"""
        response = super().post(request, *args, **kwargs)
        
        # If login was successful, check if email is verified
        if response.status_code == 200:
            email = request.data.get('email')
            if email:
                try:
                    user = User.objects.get(email=email)
                    if not user.is_email_verified:
                        return Response(
                            {
                                "detail": "Email not verified. Please check your email for the verification link.",
                                "error_code": "email_not_verified",
                                "email": email
                            },
                            status=status.HTTP_403_FORBIDDEN
                        )
                except User.DoesNotExist:
                    pass
        
        return response

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('api/', include('core.urls')),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('rss/', LatestArticlesFeed(), name='rss_feed'),
    
    # JWT Authentication Endpoints (Login)
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # App API Routes
    path('api/users/', include('users.urls')),
    path('api/news/', include('news.urls')),
    path('api/interactions/', include('interactions.urls')),
    # path('api/interactions/', include('interactions.urls')), # Ise next step mein banayenge
    path('api/newsletter/subscribe/', SubscribeNewsletterView.as_view(), name='newsletter_subscribe'),
    path('api/newsletter/unsubscribe/', UnsubscribeNewsletterView.as_view(), name='newsletter_unsubscribe'),
    path('api/contact/', ContactMessageCreateView.as_view(), name='contact_api'),
    path('api/settings/', SiteSettingAPIView.as_view(), name='site_settings'),
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    
]

# Media files ko serve karne ke liye (Images show karne ke liye)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)