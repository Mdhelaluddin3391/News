# news-backend/core/urls.py
from django.urls import path
from .views import ActiveAdsAPIView

urlpatterns = [
    path('ads/active/', ActiveAdsAPIView.as_view(), name='active-ads'),
]