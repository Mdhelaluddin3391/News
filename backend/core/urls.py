from django.urls import path

from .views import ActiveAdsAPIView, ActiveJobPostingsAPIView, AdvertisePageAPIView


urlpatterns = [
    path("ads/active/", ActiveAdsAPIView.as_view(), name="active-ads"),
    path("advertise-page/", AdvertisePageAPIView.as_view(), name="advertise-page"),
    path("jobs/active/", ActiveJobPostingsAPIView.as_view(), name="active-jobs"),
]
