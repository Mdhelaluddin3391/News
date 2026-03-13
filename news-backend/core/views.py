from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import ContactMessage
from .serializers import ContactMessageSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Advertisement
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import ContactMessage, Advertisement
from .serializers import ContactMessageSerializer, AdvertisementSerializer
from .models import ContactMessage, Advertisement, SiteSetting
from .serializers import ContactMessageSerializer, AdvertisementSerializer, SiteSettingSerializer



class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny] 


class ActiveAdsAPIView(APIView):
    # Active ads jaldi change nahi hote, isliye isko 10 minutes (60 * 10 seconds) ke liye cache karenge
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        slots = ['header', 'sidebar', 'in_article']
        ads_data = {}

        for slot in slots:
            brand_ad = Advertisement.objects.filter(slot=slot, ad_type='brand', is_active=True).first()
            if brand_ad:
                ads_data[slot] = AdvertisementSerializer(brand_ad).data
                continue 
            
            google_ad = Advertisement.objects.filter(slot=slot, ad_type='google', is_active=True).first()
            if google_ad:
                ads_data[slot] = AdvertisementSerializer(google_ad).data

        return Response(ads_data)
    
class SiteSettingAPIView(APIView):
    # Settings jaldi change nahi hoti, toh 1 ghante tak cache karenge
    @method_decorator(cache_page(60 * 60))
    def get(self, request):
        setting = SiteSetting.objects.first()
        if setting and setting.ga4_tracking_id:
            return Response(SiteSettingSerializer(setting).data)
        return Response({"ga4_tracking_id": None})