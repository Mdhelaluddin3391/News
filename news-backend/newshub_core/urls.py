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
from interactions.views import SubscribeNewsletterView, UnsubscribeNewsletterView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    
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

    
]

# Media files ko serve karne ke liye (Images show karne ke liye)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)