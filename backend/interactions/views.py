from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
import datetime
import jwt

from django.core.cache import cache
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django.db.models import F

from core.tasks import send_async_email
from .models import Bookmark, Comment, CommentReport, NewsletterSubscriber, Poll, PollOption, PushSubscription
from .serializers import BookmarkSerializer, CommentSerializer, CommentReportSerializer, PollSerializer, PushSubscriptionSerializer

User = get_user_model()


class IsCommentOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.user_id == request.user.id

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsCommentOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        article_id = self.request.query_params.get('article_id')
        queryset = Comment.objects.select_related('user', 'article').order_by('-created_at')

        if self.action in ['list', 'retrieve']:
            queryset = queryset.filter(is_active=True)
        elif self.request.user.is_staff:
            queryset = queryset.all()
        else:
            queryset = queryset.filter(user=self.request.user)

        if article_id and self.action == 'list':
            queryset = queryset.filter(article_id=article_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Bookmark.objects
            .filter(user=self.request.user)
            .select_related('article', 'article__category', 'article__author__user')
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CommentReportViewSet(viewsets.ModelViewSet):
    serializer_class = CommentReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'comment_report'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = CommentReport.objects.select_related('reported_by', 'comment', 'comment__user', 'comment__article')
        if self.request.user.is_staff:
            return queryset.order_by('-created_at')
        return queryset.filter(reported_by=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)



class SubscribeNewsletterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'newsletter'

    def post(self, request):
        raw_email = (request.data.get('email') or '').strip()
        if not raw_email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        email = User.objects.normalize_email(raw_email)
        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "Enter a valid email address."}, status=status.HTTP_400_BAD_REQUEST)

        subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
        
        if not created and subscriber.is_active:
            return Response({"message": "You are already subscribed!"}, status=status.HTTP_200_OK)
        
        subscriber.is_active = True
        subscriber.save()

        # ================== NAYA CODE: WELCOME EMAIL ==================
        if created or subscriber.is_active:
            subject = "🎉 Welcome to Ferox Times - Stay Updated!"
            message = "Thank you for subscribing to Ferox Times! You will now receive our daily top stories and breaking news alerts."
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
                    .container {{ max-width: 600px; background: white; padding: 30px; border-radius: 8px; margin: auto; border-top: 5px solid #1a365d; }}
                    h2 {{ color: #1a365d; }}
                    p {{ color: #444; line-height: 1.6; font-size: 16px; }}
                    .btn {{ display: inline-block; background: #d32f2f; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin-top: 20px; font-weight: bold; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #888; text-align: center; border-top: 1px solid #eee; padding-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Welcome to Ferox Times! 📰</h2>
                    <p>Hi there,</p>
                    <p>Thank you for subscribing! You are now part of our community. We promise to bring you the most accurate, fast, and reliable news directly to your inbox.</p>
                    <p><strong>What to expect:</strong></p>
                    <ul>
                        <li>🚨 Instant Breaking News Alerts</li>
                        <li>🌙 Daily Night Digest (Top stories of the day)</li>
                        <li>⭐ Weekend Editor's Special</li>
                    </ul>
                    <a href="{settings.FRONTEND_URL}/" class="btn" style="color: white;">Read Latest News Now</a>
                    
                    <div class="footer">
                        If you ever wish to stop receiving emails, you can <a href="{settings.FRONTEND_URL}/unsubscribe?email={email}">unsubscribe here</a>.
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Email ko background mein bhejein taaki UI slow na ho
            send_async_email.delay(subject, message, [email], html_content)

        return Response({"message": "Successfully subscribed to the newsletter!"}, status=status.HTTP_201_CREATED)



class UnsubscribeNewsletterView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'newsletter'

    def post(self, request):
        token = request.data.get('token')
        raw_email = (request.data.get('email') or '').strip()

        # === 1. CONFIRM UNSUBSCRIBE LOGIC (Agar request mein token aaya hai) ===
        if token:
            try:
                # Token verify aur decode karein
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                
                if payload.get('type') != 'unsubscribe':
                    raise jwt.InvalidTokenError
                
                sub_email = payload.get('email')
                subscriber = NewsletterSubscriber.objects.get(email=sub_email)
                
                # === NAYA: Check if token has already been used ===
                if subscriber.unsubscribe_token_used_at is not None:
                    return Response(
                        {"error": "This unsubscribe link has already been used. You are already unsubscribed."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verify that the token matches what we have stored
                if subscriber.unsubscribe_token != token:
                    return Response(
                        {"error": "Invalid or expired unsubscribe token."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # User ko inactive mark karein AND mark token as used
                subscriber.is_active = False
                subscriber.unsubscribe_token_used_at = timezone.now()
                subscriber.save()
                
                return Response({"message": "You have been successfully unsubscribed."})
                
            except jwt.ExpiredSignatureError:
                return Response({"error": "The unsubscribe link has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
            except (jwt.InvalidTokenError, NewsletterSubscriber.DoesNotExist):
                return Response({"error": "Invalid token or subscriber not found."}, status=status.HTTP_400_BAD_REQUEST)

        # === 2. REQUEST UNSUBSCRIBE LOGIC (Agar request mein email aaya hai) ===
        if raw_email:
            email = User.objects.normalize_email(raw_email)
            try:
                validate_email(email)
            except ValidationError:
                return Response({"error": "Enter a valid email address."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                subscriber = NewsletterSubscriber.objects.get(email=email)
                
                if not subscriber.is_active:
                    return Response({"message": "This email is already unsubscribed."})

                # Ek secure JWT Token Generate karein (1 Hour expiry)
                payload = {
                    'email': email,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
                    'type': 'unsubscribe'
                }
                unsub_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
                
                # === NAYA: Store token in database ===
                subscriber.unsubscribe_token = unsub_token
                subscriber.unsubscribe_token_used_at = None  # Token is newly issued, not yet used
                subscriber.save()
                
                # Unsubscribe Link banayein
                unsub_link = f"{settings.FRONTEND_URL}/unsubscribe?token={unsub_token}"
                
                # Email Bhejein
                subject = "Confirm Unsubscribe - Ferox Times"
                message = f"Please click the following link to confirm your unsubscription: {unsub_link}"
                
                html_content = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h2 style="color: #d32f2f;">Confirm Unsubscribe</h2>
                    <p>We received a request to unsubscribe this email from Ferox Times alerts.</p>
                    <p>If you wish to proceed, please click the button below. This link is valid for 1 hour.</p>
                    <a href="{unsub_link}" style="display: inline-block; padding: 12px 25px; background-color: #d32f2f; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px;">Confirm Unsubscribe</a>
                    <p style="margin-top: 20px; font-size: 12px; color: #64748b;">If you didn't request this, you can safely ignore this email.</p>
                </div>
                """
                
                # Background task call karke email bhejein
                send_async_email.delay(subject, message, [email], html_content)
                
                return Response({"message": "A secure confirmation link has been sent to your email. Please check your inbox."})
                
            except NewsletterSubscriber.DoesNotExist:
                return Response({"error": "This email is not registered in our subscriber list."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"error": "Email or token is required."}, status=status.HTTP_400_BAD_REQUEST)
        
class ActivePollView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cache_key = 'interactions:active-poll'
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        poll = Poll.objects.filter(is_active=True).first()
        if poll:
            payload = PollSerializer(poll).data
            cache.set(cache_key, payload, 60)
            return Response(payload)
        return Response({"error": "No active poll found", "active_poll_exists": False}, status=status.HTTP_200_OK)

class VotePollView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'poll_vote'

    def post(self, request, option_id):
        try:
            option = PollOption.objects.get(id=option_id)
            PollOption.objects.filter(id=option.id).update(votes=F('votes') + 1)
            option.refresh_from_db(fields=['votes'])
            cache.delete('interactions:active-poll')
            return Response({"message": "Vote successfully counted!", "votes": option.votes})
        except PollOption.DoesNotExist:
            return Response({"error": "Option not found"}, status=status.HTTP_404_NOT_FOUND)
        



class SavePushSubscriptionView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'push_subscribe'

    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            # Agar endpoint pehle se hai, toh update kar do, nahi toh naya banao
            sub, created = PushSubscription.objects.update_or_create(
                endpoint=serializer.validated_data['endpoint'],
                defaults={
                    'auth': serializer.validated_data['auth'],
                    'p256dh': serializer.validated_data['p256dh'],
                    'user': request.user if request.user.is_authenticated else None
                }
            )
            return Response({"message": "Subscription saved successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
