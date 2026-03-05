from rest_framework import serializers
from .models import Bookmark, Comment
from users.serializers import UserSerializer

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