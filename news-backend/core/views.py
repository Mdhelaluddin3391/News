from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import ContactMessage
from .serializers import ContactMessageSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Advertisement
from .serializers import AdvertisementSerializer



class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny] 


class ActiveAdsAPIView(APIView):
    def get(self, request):
        slots = ['header', 'sidebar', 'in_article']
        ads_data = {}

        for slot in slots:
            # Priority 1: Pehle check karo ki koi Active Brand Ad hai kya?
            brand_ad = Advertisement.objects.filter(slot=slot, ad_type='brand', is_active=True).first()
            if brand_ad:
                ads_data[slot] = AdvertisementSerializer(brand_ad).data
                continue # Agar brand ad mil gaya, toh Google ad mat dhundho
            
            # Priority 2: Agar Brand Ad nahi hai, toh Google Ad check karo
            google_ad = Advertisement.objects.filter(slot=slot, ad_type='google', is_active=True).first()
            if google_ad:
                ads_data[slot] = AdvertisementSerializer(google_ad).data

        return Response(ads_data)