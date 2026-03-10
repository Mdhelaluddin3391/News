from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CommentViewSet, BookmarkViewSet
from .views import SubscribeNewsletterView, UnsubscribeNewsletterView, ActivePollView, VotePollView
from .views import SavePushSubscriptionView


router = DefaultRouter()
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')

urlpatterns = [
    path('', include(router.urls)),
    path('polls/active/', ActivePollView.as_view(), name='active-poll'),
    path('polls/vote/<int:option_id>/', VotePollView.as_view(), name='vote-poll'),
    path('push/subscribe/', SavePushSubscriptionView.as_view(), name='push-subscribe'),
]