from rest_framework import serializers
from .models import Article, Category, Author, Tag, LiveUpdate


class LiveUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveUpdate
        fields = ('id', 'title', 'content', 'timestamp')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')

class AuthorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    username = serializers.CharField(source='slug', read_only=True)
    slug = serializers.CharField(read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    bio = serializers.CharField(source='user.bio', read_only=True)
    
    class Meta:
        model = Author
        fields = ('id', 'name', 'username', 'slug', 'profile_picture', 'bio', 'role', 'twitter_url', 'linkedin_url')

class ArticleSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True,
    )
    author = AuthorSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='tags',
    )
    live_updates = LiveUpdateSerializer(many=True, read_only=True)

    # ── Supporting Document (evidence) ──
    # Write-only: Public API se file URL expose nahi hoti.
    # Sirf editorial team Django admin se dekh sakti hai.
    supporting_document = serializers.FileField(
        write_only=True,
        required=False,
        allow_null=True,
    )
    writer_notes = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'category', 'author', 'source_name',
            'description', 'content', 'featured_image', 'published_at',
            'views', 'is_featured', 'is_trending', 'is_breaking',
            'is_editors_pick', 'tags', 'is_top_story', 'is_live', 'live_updates',
            'updated_at', 'category_id', 'tag_ids', 'status', 'source_url',
            'is_imported', 'is_web_story', 'post_to_facebook', 'post_to_twitter',
            'post_to_telegram',
            # Evidence fields (write_only above)
            'supporting_document', 'writer_notes',
        )

        read_only_fields = ('views', 'published_at', 'updated_at', 'is_imported')

    def validate_title(self, value):
        cleaned_value = value.strip()
        if len(cleaned_value) < 5:
            raise serializers.ValidationError('Title must contain at least 5 characters.')
        return cleaned_value

    def validate_description(self, value):
        cleaned_value = value.strip()
        if len(cleaned_value) < 20:
            raise serializers.ValidationError('Description must contain at least 20 characters.')
        return cleaned_value

    def validate_supporting_document(self, value):
        if value is None:
            return value
        # Max 20 MB
        max_size = 20 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError('Supporting document must be smaller than 20 MB.')
        allowed_types = [
            'application/pdf',
            'image/jpeg', 'image/png',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'video/mp4',
            'audio/mpeg',
            'application/zip',
        ]
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError(
                'Unsupported file type. Accepted: PDF, JPG, PNG, DOCX, MP4, MP3, ZIP.'
            )
        return value
