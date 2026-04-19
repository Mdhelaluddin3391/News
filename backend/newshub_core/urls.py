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
from django.contrib.auth import get_user_model
from django.contrib.sitemaps.views import sitemap
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.health_views import DatabaseHealthCheckView, HealthCheckView, RedisHealthCheckView
from core.views import ContactMessageCreateView, SiteSettingAPIView
from interactions.views import SubscribeNewsletterView, UnsubscribeNewsletterView
from news.feeds import LatestArticlesFeed
from news.sitemaps import ArticleSitemap, AuthorSitemap, CategorySitemap, TagSitemap
from users.views import CookieTokenRefreshView, CsrfCookieView, LogoutView, set_auth_cookies
from news.admin_views import AIArticleWriterView
from news.debug_views import TelegramTestView

User = get_user_model()


sitemaps = {
    'articles': ArticleSitemap,
    'categories': CategorySitemap,
    'authors': AuthorSitemap,
    'tags': TagSitemap,
}

class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        if not email or not password:
            return response

        user = User.objects.filter(email__iexact=email).first()
        if user and not user.is_email_verified and user.check_password(password):
            return Response(
                {
                    "detail": "Email not verified. Please check your inbox for the verification link.",
                    "error_code": "email_not_verified",
                    "email": user.email,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if response.status_code == status.HTTP_200_OK and "refresh" in response.data:
            refresh = response.data["refresh"]
            response.data = {"message": "Login successful."}
            set_auth_cookies(response, refresh=RefreshToken(refresh))

        return response

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('health/db/', DatabaseHealthCheckView.as_view(), name='health_check_db'),
    path('health/redis/', RedisHealthCheckView.as_view(), name='health_check_redis'),
    path('admin/news/ai-writer/', AIArticleWriterView.as_view(), name='admin-ai-writer'),
    path('admin/news/telegram-test/', TelegramTestView.as_view(), name='admin-telegram-test'),
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('api/', include('core.urls')),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('rss/', LatestArticlesFeed(), name='rss_feed'),
    
    # App API Routes
    path('api/users/', include('users.urls')),
    path('api/news/', include('news.urls')),
    path('api/interactions/', include('interactions.urls')),
    path('api/newsletter/subscribe/', SubscribeNewsletterView.as_view(), name='newsletter_subscribe'),
    path('api/newsletter/unsubscribe/', UnsubscribeNewsletterView.as_view(), name='newsletter_unsubscribe'),
    path('api/contact/', ContactMessageCreateView.as_view(), name='contact_api'),
    path('api/settings/', SiteSettingAPIView.as_view(), name='site_settings'),
    path('api/auth/csrf/', CsrfCookieView.as_view(), name='auth_csrf'),
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth_logout'),

    
]

# Media files ko serve karne ke liye (Images show karne ke liye)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
