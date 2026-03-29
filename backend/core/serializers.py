from rest_framework import serializers
from .models import Advertisement, ContactMessage, SiteSetting
from .models import ContactMessage
from .models import Advertisement, ContactMessage, SiteSetting, JobPosting


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at']

class AdvertisementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertisement
        fields = ['id', 'slot', 'ad_type', 'image', 'url', 'google_ad_code']

class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = ['ga4_tracking_id']

class JobPostingSerializer(serializers.ModelSerializer):
    # Display name nikalne ke liye (e.g., 'full_time' ko 'Full-Time' dikhane ke liye)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)

    class Meta:
        model = JobPosting
        fields = ['id', 'title', 'location', 'employment_type_display', 'description', 'created_at']