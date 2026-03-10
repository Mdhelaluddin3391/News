from rest_framework import serializers
from .models import Bookmark, Comment
from users.serializers import UserSerializer
from .models import Poll, PollOption
from .models import PushSubscription


class CommentSerializer(serializers.ModelSerializer):
    # Comment kisne kiya hai, uski detail read-only format mein
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'article', 'user_detail', 'text', 'is_active', 'created_at')
        read_only_fields = ('id', 'is_active', 'created_at')

class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ('id', 'article', 'created_at')
        read_only_fields = ('id', 'created_at')


class PollOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollOption
        fields = ['id', 'text', 'votes']

class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    total_votes = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ['id', 'question', 'description', 'is_active', 'options', 'total_votes']

    def get_total_votes(self, obj):
        return sum(option.votes for option in obj.options.all())
    


class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ['endpoint', 'auth', 'p256dh']