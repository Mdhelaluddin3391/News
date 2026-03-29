from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class CookieAuthApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='cookie-user@example.com',
            name='Cookie User',
            password='StrongPass123!',
            is_active=True,
            is_email_verified=True,
        )

    def test_login_sets_http_only_auth_cookies(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': self.user.email, 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS'], response.cookies)
        self.assertIn(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'], response.cookies)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_refresh_uses_cookie_when_request_body_has_no_token(self):
        login_response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': self.user.email, 'password': 'StrongPass123!'},
            format='json',
        )
        refresh_cookie = login_response.cookies[settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']].value
        self.client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH']] = refresh_cookie

        response = self.client.post(reverse('token_refresh'), {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Session refreshed.')
        self.assertIn(settings.SIMPLE_JWT['AUTH_COOKIE_ACCESS'], response.cookies)
