from rest_framework import serializers
from .models import Article, Category, Author

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')

class AuthorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    bio = serializers.CharField(source='user.bio', read_only=True) # Naya field add kiya
    
    class Meta:
        model = Author
        # fields mein 'bio' ko bhi shamil kar diya hai
        fields = ('id', 'name', 'profile_picture', 'bio', 'role', 'twitter_url', 'linkedin_url')

class ArticleSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'category', 'author', 'source_name', 
            'description', 'content', 'featured_image', 'published_at', 
            'views', 'is_featured', 'is_trending', 'is_breaking'
        )