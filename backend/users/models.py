import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from core.models import BaseModel

class UserManager(BaseUserManager):
    """Custom manager email base login ke liye"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)
        extra_fields.setdefault("role", "admin")
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser, BaseModel):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('reporter', 'Reporter'),
        ('author', 'Author'),
        ('subscriber', 'Subscriber'),
    )

    username = None
    email = models.EmailField(unique=True, verbose_name="Email Address")
    name = models.CharField(max_length=255)
    
    # Role field
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='subscriber')
    
    profile_picture = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    # Activist Fields
    is_activist_applicant = models.BooleanField(
        default=False, 
        help_text="Has the subscriber applied to become an activist?"
    )
    is_activist_approved = models.BooleanField(
        default=False,
        help_text="Is the user officially approved as a verified guest writer?"
    )

    # Email Verification Fields
    is_email_verified = models.BooleanField(default=False, help_text="Is the email address verified?")
    email_verification_token = models.CharField(
        max_length=255, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Unique token for email verification"
    )
    email_verification_token_created_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When was the verification token created"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()
    EMAIL_VERIFICATION_TTL = timedelta(hours=24)

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    def generate_email_verification_token(self):
        """Generate a fresh one-time token for email verification."""
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_token_created_at = timezone.now()
        self.save(update_fields=["email_verification_token", "email_verification_token_created_at"])
        return self.email_verification_token

    def has_valid_email_verification_token(self):
        if not self.email_verification_token or not self.email_verification_token_created_at:
            return False
        return timezone.now() - self.email_verification_token_created_at <= self.EMAIL_VERIFICATION_TTL

    def clear_email_verification_token(self):
        self.email_verification_token = None
        self.email_verification_token_created_at = None

    def mark_email_verified(self):
        self.is_email_verified = True
        self.is_active = True
        self.clear_email_verification_token()
        self.save(
            update_fields=[
                "is_email_verified",
                "is_active",
                "email_verification_token",
                "email_verification_token_created_at",
            ]
        )

    def verify_email(self, token):
        """Verify email with token and check expiration."""
        if token != self.email_verification_token:
            return False

        if not self.has_valid_email_verification_token():
            return False

        self.mark_email_verified()
        return True
