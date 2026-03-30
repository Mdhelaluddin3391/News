from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Advertisement, AdvertiseOption, AdvertisePage


class AdvertisePageAPITests(APITestCase):
    def test_returns_defaults_when_no_admin_content_exists(self):
        response = self.client.get(reverse("advertise-page"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["hero_title"], "Grow Your Brand With Forex Times")
        self.assertGreaterEqual(len(response.data["options"]), 3)

    def test_returns_admin_managed_page_content(self):
        page = AdvertisePage.objects.first()
        page.hero_title = "Advertise On Our Network"
        page.hero_description = "Reach decision makers."
        page.slots_section_title = "Current Opportunities"
        page.inquiry_title = "Start Your Campaign"
        page.inquiry_description = "Tell us what you need."
        page.submit_button_text = "Send Campaign Brief"
        page.success_message = "We received your campaign brief."
        page.save()
        AdvertiseOption.objects.all().delete()
        AdvertiseOption.objects.create(
            title="Homepage Spotlight",
            description="Premium homepage placement.",
            icon_class="fas fa-star",
            inquiry_value="Homepage Spotlight",
            sort_order=1,
        )

        response = self.client.get(reverse("advertise-page"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["hero_title"], "Advertise On Our Network")
        self.assertEqual(response.data["submit_button_text"], "Send Campaign Brief")
        self.assertEqual(len(response.data["options"]), 1)
        self.assertEqual(response.data["options"][0]["title"], "Homepage Spotlight")


class ActiveAdsAPITests(APITestCase):
    def test_desktop_prefers_highest_priority_non_mobile_ad(self):
        Advertisement.objects.create(
            title="Low Priority Header",
            slot="header",
            ad_type="google",
            google_ad_code="<div>low</div>",
            priority=1,
            is_active=True,
        )
        Advertisement.objects.create(
            title="High Priority Header",
            slot="header",
            ad_type="google",
            google_ad_code="<div>high</div>",
            priority=10,
            is_active=True,
        )

        response = self.client.get(reverse("active-ads"), HTTP_USER_AGENT="Mozilla/5.0 (X11; Linux x86_64)")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["header"]["google_ad_code"], "<div>high</div>")

    def test_mobile_can_receive_mobile_only_ad(self):
        Advertisement.objects.create(
            title="Desktop Sidebar",
            slot="sidebar",
            ad_type="google",
            google_ad_code="<div>desktop</div>",
            priority=5,
            is_active=True,
        )
        Advertisement.objects.create(
            title="Mobile Sidebar",
            slot="sidebar",
            ad_type="google",
            google_ad_code="<div>mobile</div>",
            priority=1,
            is_active=True,
            is_mobile_only=True,
        )

        response = self.client.get(
            reverse("active-ads"),
            HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["sidebar"]["google_ad_code"], "<div>mobile</div>")
