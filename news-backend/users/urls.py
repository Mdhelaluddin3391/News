from django.urls import path
from .views import RegisterView, ProfileView, ForgotPasswordView, ResetPasswordView, GoogleLoginView, VerifyEmailView, ResendVerificationEmailView

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
]