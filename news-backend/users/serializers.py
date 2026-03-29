from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'profile_picture', 'bio', 'role', 'is_email_verified', 'created_at')
        read_only_fields = ('id', 'email', 'role', 'is_email_verified', 'created_at')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ('name', 'email', 'password')

    def create(self, validated_data):
        # Create user with is_active=False (inactive until email is verified)
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password'],
            role='subscriber',
            is_active=False  # Keep user inactive until email verification
        )
        return user