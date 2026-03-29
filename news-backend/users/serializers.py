from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'profile_picture', 'bio', 'role', 'is_email_verified', 'created_at')
        read_only_fields = ('id', 'email', 'role', 'is_email_verified', 'created_at')


class ProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'profile_picture', 'bio', 'role', 'is_email_verified', 'created_at', 'password')
        read_only_fields = ('id', 'email', 'role', 'is_email_verified', 'created_at')

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("name", "email", "password")

    def validate_email(self, value):
        email = User.objects.normalize_email(value.strip())
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            name=validated_data["name"],
            password=validated_data["password"],
            role="subscriber",
            is_active=False,
            is_email_verified=False,
        )
        return user
