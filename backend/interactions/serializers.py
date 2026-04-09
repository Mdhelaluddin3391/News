import bleach
from urllib.parse import urlparse
from rest_framework import serializers

from users.serializers import UserSerializer
from .models import Bookmark, Comment, CommentReport, Poll, PollOption, PushSubscription


class CommentSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    
    # SECURITY FIX: Enforce max_length to prevent Bleach CPU Exhaustion DoS
    text = serializers.CharField(max_length=1500, trim_whitespace=True)

    class Meta:
        model = Comment
        fields = ('id', 'article', 'user_detail', 'text', 'is_active', 'created_at')
        read_only_fields = ('id', 'is_active', 'created_at')

    def validate_text(self, value):
        # Bleach is now safe to run because max_length prevents massive payloads
        cleaned_value = bleach.clean(value, tags=[], strip=True).strip()
        if len(cleaned_value) < 2:
            raise serializers.ValidationError('Comment must contain at least 2 characters.')
        return cleaned_value


class CommentReportSerializer(serializers.ModelSerializer):
    reported_by_detail = UserSerializer(source='reported_by', read_only=True)
    comment_detail = CommentSerializer(source='comment', read_only=True)
    
    # SECURITY FIX: Limit payload size to prevent database DoS
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, trim_whitespace=True)

    class Meta:
        model = CommentReport
        fields = ('id', 'comment', 'comment_detail', 'reported_by_detail', 'reason', 'description', 
                  'is_reviewed', 'admin_action', 'admin_notes', 'created_at')
        read_only_fields = ('id', 'reported_by_detail', 'comment_detail', 'is_reviewed', 'admin_action', 'admin_notes', 'created_at')

    def validate_comment(self, value):
        if not value.is_active:
            raise serializers.ValidationError('This comment is no longer available to report.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        comment = attrs.get('comment')

        if request is None or not request.user.is_authenticated:
            return attrs

        if comment.user_id == request.user.id:
            raise serializers.ValidationError({'comment': 'You cannot report your own comment.'})

        if CommentReport.objects.filter(comment=comment, reported_by=request.user).exists():
            raise serializers.ValidationError({'detail': 'You have already reported this comment.'})

        return attrs


class BookmarkSerializer(serializers.ModelSerializer):
    def validate_article(self, value):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if Bookmark.objects.filter(user=request.user, article=value).exists():
                raise serializers.ValidationError('This article is already saved.')
        return value

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
    
    def validate_endpoint(self, value):
        # SECURITY FIX: Protect against Server-Side Request Forgery (SSRF)
        if not value.startswith('https://'):
            raise serializers.ValidationError('Push endpoint must be a secure HTTPS URL.')
        
        parsed = urlparse(value)
        # Block internal network IPs so attackers cannot port-scan your internal AWS/Docker infrastructure
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0'] or \
           str(parsed.hostname).startswith(('192.168.', '10.', '172.')):
            raise serializers.ValidationError('Invalid push endpoint. Localhost/Internal IPs are forbidden.')
            
        return value

    class Meta:
        model = PushSubscription
        fields = ['endpoint', 'auth', 'p256dh']