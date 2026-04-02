import bleach
from rest_framework import serializers

from .models import (
    Advertisement,
    AdvertiseOption,
    ContactMessage,
    JobPosting,
    SiteSetting,
)


class ContactMessageSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        cleaned_value = bleach.clean(value, tags=[], strip=True).strip()
        if len(cleaned_value) < 2:
            raise serializers.ValidationError("Name must contain at least 2 characters.")
        return cleaned_value

    def validate_subject(self, value):
        cleaned_value = bleach.clean(value, tags=[], strip=True).strip()
        if len(cleaned_value) < 3:
            raise serializers.ValidationError("Subject must contain at least 3 characters.")
        return cleaned_value

    def validate_message(self, value):
        cleaned_value = bleach.clean(value, tags=[], strip=True).strip()
        if len(cleaned_value) < 10:
            raise serializers.ValidationError("Message must contain at least 10 characters.")
        return cleaned_value

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
