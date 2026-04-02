from django.conf import settings
from django.core.cache import cache
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .cache_keys import ACTIVE_JOBS_CACHE_KEY, ADVERTISE_PAGE_CACHE_KEY, SITE_SETTINGS_CACHE_KEY, active_ads_cache_key
from .models import Advertisement, AdvertiseOption, AdvertisePage, ContactMessage, JobPosting, SiteSetting
from .serializers import (
    AdvertisementSerializer,
    AdvertiseOptionSerializer,
    ContactMessageSerializer,
    JobPostingSerializer,
    SiteSettingSerializer,
)


DEFAULT_ADVERTISE_PAGE = {
    "hero_title": "Grow Your Brand With Ferox Times",
    "hero_description": (
        "Reach a highly engaged audience through our premium digital news platform. "
        "We offer strategic ad placements to maximize your visibility."
    ),
    "slots_section_title": "Available Ad Slots",
    "inquiry_title": "Advertisement Inquiry",
    "inquiry_description": (
        "Fill out the form below and our advertising team will get back to you with "
        "pricing and analytics details."
    ),
    "submit_button_text": "Submit Inquiry",
    "success_message": "Thank you for your interest! Our advertising team will contact you shortly.",
    "options": [
        {
            "title": "Header Banner",
            "description": (
                "Premium visibility at the very top of our website. Appears on all "
                "pages. Highly recommended for maximum reach."
            ),
            "icon_class": "fas fa-rectangle-ad",
            "inquiry_value": "Header Banner",
            "sort_order": 1,
            "show_on_page": True,
            "show_in_inquiry_form": True,
        },
        {
            "title": "Sidebar Top",
            "description": (
                "Sticky advertisement on the right sidebar. Stays visible as users "
                "scroll through breaking news and articles."
            ),
            "icon_class": "fas fa-border-all",
            "inquiry_value": "Sidebar Ad",
            "sort_order": 2,
            "show_on_page": True,
            "show_in_inquiry_form": True,
        },
        {
            "title": "In-Article Ad",
            "description": (
                "Placed directly inside our news articles. Great for capturing the "
                "attention of highly engaged readers."
            ),
            "icon_class": "fas fa-newspaper",
            "inquiry_value": "In-Article Ad",
            "sort_order": 3,
            "show_on_page": True,
            "show_in_inquiry_form": True,
        },
        {
            "title": "Brand Collaboration",
            "description": (
                "Sponsored posts, brand campaigns, and custom integrations tailored "
                "to your launch timeline and audience goals."
            ),
            "icon_class": "fas fa-handshake",
            "inquiry_value": "Brand Collaboration / Sponsored Post",
            "sort_order": 4,
            "show_on_page": False,
            "show_in_inquiry_form": True,
        },
        {
            "title": "Consultation",
            "description": "Need help selecting a package? Our team can suggest the right placement mix.",
            "icon_class": "fas fa-comments",
            "inquiry_value": "Not sure yet, need consultation",
            "sort_order": 5,
            "show_on_page": False,
            "show_in_inquiry_form": True,
        },
    ],
}


def _is_mobile_request(request):
    user_agent = (request.headers.get("User-Agent") or "").lower()
    mobile_markers = ("mobile", "android", "iphone", "ipad", "ipod")
    return any(marker in user_agent for marker in mobile_markers)


def _build_advertise_page_payload():
    page = AdvertisePage.objects.first()
    options = AdvertiseOption.objects.filter(is_active=True).order_by("sort_order", "id")

    payload = dict(DEFAULT_ADVERTISE_PAGE)
    payload["options"] = [dict(option) for option in DEFAULT_ADVERTISE_PAGE["options"]]

    if page:
        payload.update(
            {
                "hero_title": page.hero_title,
                "hero_description": page.hero_description,
                "slots_section_title": page.slots_section_title,
                "inquiry_title": page.inquiry_title,
                "inquiry_description": page.inquiry_description,
                "submit_button_text": page.submit_button_text,
                "success_message": page.success_message,
            }
        )

    if options.exists():
        payload["options"] = AdvertiseOptionSerializer(options, many=True).data

    return payload


class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact_form"


class ActiveAdsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        slots = ["header", "sidebar", "in_article"]
        ads_data = {}
        is_mobile = _is_mobile_request(request)
        cache_key = active_ads_cache_key(is_mobile)
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        for slot in slots:
            slot_ads = Advertisement.objects.filter(slot=slot, is_active=True)
            if is_mobile:
                slot_ads = slot_ads.order_by("-is_mobile_only", "-priority", "-created_at")
            else:
                slot_ads = slot_ads.filter(is_mobile_only=False).order_by("-priority", "-created_at")

            ad = slot_ads.first()
            if ad:
                ads_data[slot] = AdvertisementSerializer(ad, context={"request": request}).data

        cache.set(cache_key, ads_data, settings.PUBLIC_API_CACHE_TTL)
        return Response(ads_data)


class AdvertisePageAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request):
        cached_payload = cache.get(ADVERTISE_PAGE_CACHE_KEY)
        if cached_payload is not None:
            return Response(cached_payload)

        payload = _build_advertise_page_payload()
        cache.set(ADVERTISE_PAGE_CACHE_KEY, payload, settings.PUBLIC_API_CACHE_TTL)
        return Response(payload)


class SiteSettingAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, _request):
        cached_payload = cache.get(SITE_SETTINGS_CACHE_KEY)
        if cached_payload is not None:
            return Response(cached_payload)

        setting = SiteSetting.objects.first()
        if setting and setting.ga4_tracking_id:
            payload = SiteSettingSerializer(setting).data
        else:
            payload = {"ga4_tracking_id": None}

        cache.set(SITE_SETTINGS_CACHE_KEY, payload, settings.SITE_SETTINGS_CACHE_TTL)
        return Response(payload)


class ActiveJobPostingsAPIView(generics.ListAPIView):
    queryset = JobPosting.objects.filter(is_active=True).order_by("-created_at")
    serializer_class = JobPostingSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        cached_payload = cache.get(ACTIVE_JOBS_CACHE_KEY)
        if cached_payload is not None:
            return Response(cached_payload)

        response = super().list(request, *args, **kwargs)
        cache.set(ACTIVE_JOBS_CACHE_KEY, response.data, settings.PUBLIC_API_CACHE_TTL)
        return response
