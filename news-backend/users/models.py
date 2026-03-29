from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from core.models import BaseModel
import uuid
from django.utils import timezone

class UserManager(BaseUserManager):
    """Custom manager email base login ke liye"""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin') # Automatically make superusers 'admin'
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

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    def generate_email_verification_token(self):
        """Generate a unique email verification token"""
        self.email_verification_token = str(uuid.uuid4())
        self.email_verification_token_created_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_token_created_at'])
        return self.email_verification_token
    
    def verify_email(self, token):
        """Verify email with token and check expiration"""
        if token != self.email_verification_token:
            return False
        
        # Check if token is still valid (24 hours)
        from datetime import timedelta
        if timezone.now() - self.email_verification_token_created_at > timedelta(hours=24):
            return False
        
        self.is_email_verified = True
        self.is_active = True  # Activate user after email verification
        self.email_verification_token = None  # Clear the token (one-time use)
        self.email_verification_token_created_at = None
        self.save(update_fields=['is_email_verified', 'is_active', 'email_verification_token', 'email_verification_token_created_at'])
        return True