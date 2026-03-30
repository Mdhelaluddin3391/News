from rest_framework import serializers

from .models import (
    Advertisement,
    AdvertiseOption,
    ContactMessage,
    JobPosting,
    SiteSetting,
)


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "subject", "message", "created_at"]


class AdvertisementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertisement
        fields = ["id", "slot", "ad_type", "image", "url", "google_ad_code"]


class AdvertiseOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvertiseOption
        fields = [
            "id",
            "title",
            "description",
            "icon_class",
            "inquiry_value",
            "sort_order",
            "show_on_page",
            "show_in_inquiry_form",
        ]


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = ["ga4_tracking_id"]


class JobPostingSerializer(serializers.ModelSerializer):
    employment_type_display = serializers.CharField(
        source="get_employment_type_display",
        read_only=True,
    )

    class Meta:
        model = JobPosting
        fields = [
            "id",
            "title",
            "location",
            "employment_type_display",
            "description",
            "created_at",
        ]
