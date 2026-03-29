from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from interactions.models import Comment, CommentReport
from news.models import Article, Category

User = get_user_model()


class CommentModerationApiTests(APITestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(
            email='reporter@example.com',
            name='Reporter',
            password='StrongPass123!',
            is_active=True,
            is_email_verified=True,
        )
        self.author = User.objects.create_user(
            email='author@example.com',
            name='Author',
            password='StrongPass123!',
            is_active=True,
            is_email_verified=True,
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            name='Other User',
            password='StrongPass123!',
            is_active=True,
            is_email_verified=True,
        )
        self.category = Category.objects.create(name='World', slug='world')
        self.article = Article.objects.create(
            title='Test Article',
            slug='test-article',
            category=self.category,
            description='Summary',
            content='Body',
            status='published',
        )
        self.comment = Comment.objects.create(
            article=self.article,
            user=self.author,
            text='This is a test comment',
        )

    def authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_user_can_report_comment_once_but_not_twice(self):
        self.authenticate(self.reporter)
        url = reverse('comment-report-list')

        first_response = self.client.post(
            url,
            {'comment': self.comment.id, 'reason': 'spam', 'description': 'Looks like spam'},
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CommentReport.objects.count(), 1)

        second_response = self.client.post(
            url,
            {'comment': self.comment.id, 'reason': 'spam'},
            format='json',
        )
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', second_response.data)

    def test_user_cannot_report_own_comment(self):
        self.authenticate(self.author)
        url = reverse('comment-report-list')

        response = self.client.post(
            url,
            {'comment': self.comment.id, 'reason': 'other', 'description': 'Self-report'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comment', response.data)

    def test_only_comment_owner_can_delete_comment(self):
        url = reverse('comment-detail', kwargs={'pk': self.comment.id})

        self.authenticate(self.other_user)
        forbidden_response = self.client.delete(url)
        self.assertEqual(forbidden_response.status_code, status.HTTP_404_NOT_FOUND)
        self.comment.refresh_from_db()
        self.assertTrue(Comment.objects.filter(pk=self.comment.id).exists())

        self.authenticate(self.author)
        allowed_response = self.client.delete(url)
        self.assertEqual(allowed_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(pk=self.comment.id).exists())
