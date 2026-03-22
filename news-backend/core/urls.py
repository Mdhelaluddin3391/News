# news-backend/core/urls.py
from django.urls import path
from .views import ActiveAdsAPIView
from .views import ActiveAdsAPIView, ActiveJobPostingsAPIView # Import add kiya

urlpatterns = [
    path('ads/active/', ActiveAdsAPIView.as_view(), name='active-ads'),
    path('jobs/active/', ActiveJobPostingsAPIView.as_view(), name='active-jobs'), # Nayi API
]