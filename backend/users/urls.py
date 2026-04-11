from django.urls import path
from .views import (
    ForgotPasswordView,
    GoogleLoginView,
    ProfileView,
    RegisterView,
    ResendVerificationEmailView,
    ResetPasswordView,
    VerifyEmailView,
    ApplyActivistView,
    ApproveActivistView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Email Verification
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification-email/', ResendVerificationEmailView.as_view(), name='resend-verification-email'),
    
    # Password Reset
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    
    # Activist Application
    path('apply-activist/', ApplyActivistView.as_view(), name='apply-activist'),
    path('approve-activist/<int:user_id>/', ApproveActivistView.as_view(), name='approve-activist'),
]
