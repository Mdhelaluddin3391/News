from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse
from rest_framework.test import APITestCase

from news.models import Article, Author, Category

User = get_user_model()


class ArticleSearchApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='search-author@example.com',
            name='Search Author',
            password='StrongPass123!',
            is_active=True,
            is_email_verified=True,
        )
        cls.author = Author.objects.create(user=cls.user, role='Senior Reporter')
        cls.category = Category.objects.create(name='Business', slug='business')
        cls.primary_article = Article.objects.create(
            title='Global inflation outlook improves',
            slug='global-inflation-outlook-improves',
            category=cls.category,
            author=cls.author,
            description='Inflation trends are improving across major economies.',
            content='Analysts expect the inflation outlook to stabilise through the year.',
            status='published',
        )
        cls.secondary_article = Article.objects.create(
            title='Markets close mixed after rate decision',
            slug='markets-close-mixed-after-rate-decision',
            category=cls.category,
            author=cls.author,
            description='Stocks were mixed after the latest central bank announcement.',
            content='Investors weighed the latest rate decision against growth concerns.',
            status='published',
        )

    def test_search_query_returns_matching_article(self):
        if connection.vendor != 'postgresql':
            self.skipTest('PostgreSQL full-text search is only available on PostgreSQL backends.')

        response = self.client.get(reverse('article-list'), {'search': 'inflation outlook'})

        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.primary_article.id)

    def test_slug_is_unique_with_uuid_suffix_on_conflict(self):
        existing_slug = 'duplicate-article'
        Article.objects.create(
            title='Duplicate Article',
            slug=existing_slug,
            category=self.category,
            author=self.author,
            description='First.
',
            content='First content.',
            status='published',
        )

        second = Article.objects.create(
            title='Duplicate Article',
            category=self.category,
            author=self.author,
            description='Second content.',
            content='Second content.',
            status='published',
        )

        self.assertNotEqual(second.slug, existing_slug)
        self.assertTrue(second.slug.startswith(existing_slug + '-'))
        self.assertEqual(len(second.slug), len(existing_slug) + 1 + 6)

    def test_retrieve_article_by_slug(self):
        response = self.client.get(reverse('article-detail', kwargs={'slug': self.primary_article.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['slug'], self.primary_article.slug)
