import datetime
import logging

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.template.loader import render_to_string
from core.tasks import send_async_email
from .serializers import (
    EmailOnlySerializer,
    GoogleLoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    TokenOnlySerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def set_auth_cookies(response, refresh):
    access_cookie = settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS"]
    refresh_cookie = settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"]
    secure = settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"]
    httponly = settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"]
    same_site = settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"]
    cookie_path = settings.SIMPLE_JWT["AUTH_COOKIE_PATH"]
    refresh_path = settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH_PATH"]

    response.set_cookie(
        access_cookie,
        str(refresh.access_token),
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        secure=secure,
        httponly=httponly,
        samesite=same_site,
        path=cookie_path,
    )
    response.set_cookie(
        refresh_cookie,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        secure=secure,
        httponly=httponly,
        samesite=same_site,
        path=refresh_path,
    )


def clear_auth_cookies(response):
    response.delete_cookie(
        settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS"],
        path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
        samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
    )
    response.delete_cookie(
        settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"],
        path=settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH_PATH"],
        samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
    )


def build_verification_link(user):
    return f"{settings.FRONTEND_URL}/verify-email?token={user.email_verification_token}"


def send_verification_email(user, regenerate_token=False):
    if regenerate_token or not user.has_valid_email_verification_token():
        user.generate_email_verification_token()

    verification_link = build_verification_link(user)
    subject = "Verify Your Email - Ferox Times"
    
    context = {
        'user_name': user.name,
        'verification_link': verification_link,
        'verification_token': user.email_verification_token
    }
    
    # IMPROVEMENT: Use Django templates instead of hardcoded HTML strings
    text_content = render_to_string('emails/verify_email.txt', context)
    html_content = render_to_string('emails/verify_email.html', context)

    send_async_email.delay(subject, text_content, [user.email], html_content)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        email_sent = True
        try:
            transaction.on_commit(lambda: send_verification_email(user))
        except Exception:
            email_sent = False
            logger.exception("Failed to send verification email for %s", user.email)

        response_payload = {
            "message": (
                "Registration successful. Check your inbox to verify your email."
                if email_sent
                else "Registration successful, but we could not send the verification email. Please request a new one."
            ),
            "email": user.email,
            "verification_required": True,
            "email_sent": email_sent,
        }
        return Response(response_payload, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = TokenOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"].strip()

        user = User.objects.filter(email_verification_token=token).first()
        if not user:
            return Response(
                {"error": "Invalid or already used verification token."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.has_valid_email_verification_token():
            return Response(
                {"error": "Verification token has expired. Request a new verification email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.mark_email_verified()
        return Response(
            {
                "message": "Email verified successfully. Your account is now active.",
                "is_verified": True,
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationEmailView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_alert"

    def post(self, request):
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()

        if user and not user.is_email_verified:
            try:
                transaction.on_commit(lambda: send_verification_email(user, regenerate_token=True))
            except Exception:
                logger.exception("Failed to resend verification email for %s", email)
                return Response(
                    {"error": "We could not send the verification email right now. Please try again later."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response(
            {"message": "If this account is waiting for verification, a new email has been sent."},
            status=status.HTTP_200_OK,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response({"detail": "CSRF cookie set.", "csrfToken": get_token(request)})


class CookieTokenRefreshView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"]) or request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token not found."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        serializer.is_valid(raise_exception=True)

        response = Response({"message": "Session refreshed."}, status=status.HTTP_200_OK)
        set_auth_cookies(response, RefreshToken(refresh_token))
        return response


class LogoutView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        response = Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response


class ForgotPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_alert"

    def post(self, request):
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            
            # SECURITY FIX: Tie the JWT to the current password hash so it invalidates immediately upon use
            payload = {
                "user_id": user.id,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
                "type": "reset_password",
                "pwd_hash": user.password[-10:] 
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            context = {'user_name': user.name, 'reset_link': reset_link}
            text_content = render_to_string('emails/reset_password.txt', context)
            html_content = render_to_string('emails/reset_password.html', context)

            send_async_email.delay("Password Reset Request - Ferox Times", text_content, [user.email], html_content)
        except User.DoesNotExist:
            pass # Prevent user enumeration

        return Response({"message": "If that email is registered, we have sent a reset link."})

class ResetPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            payload = jwt.decode(serializer.validated_data["token"], settings.SECRET_KEY, algorithms=["HS256"])
            if payload.get("type") != "reset_password":
                raise jwt.InvalidTokenError

            user = User.objects.get(id=payload["user_id"])
            
            # SECURITY FIX: Validate that the password hasn't been changed since the token was issued
            if payload.get("pwd_hash") != user.password[-10:]:
                raise jwt.InvalidTokenError

            user.set_password(serializer.validated_data["password"])
            user.save(update_fields=["password"])
            return Response({"message": "Password reset successful."})
            
        except jwt.ExpiredSignatureError:
            return Response({"error": "The reset link has expired."}, status=status.HTTP_400_BAD_REQUEST)
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return Response({"error": "Invalid or already used reset link."}, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            idinfo = id_token.verify_oauth2_token(
                serializer.validated_data["token"], 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )

            email = User.objects.normalize_email(idinfo["email"])
            
            # CLEANUP: Streamlined object creation and default overrides
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "name": idinfo.get("name", "Google User"),
                    "role": "subscriber",
                    "is_active": True,
                    "is_email_verified": True,
                },
            )

            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])

            refresh = RefreshToken.for_user(user)
            response = Response({"message": "Login successful.", "user": UserSerializer(user).data})
            set_auth_cookies(response, refresh)
            return response
            
        except ValueError:
            return Response({"error": "Invalid Google Token"}, status=status.HTTP_400_BAD_REQUEST)