import threading
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from core.tasks import send_async_email
from .models import Bookmark, Comment, NewsletterSubscriber, Poll, PollOption, PushSubscription
from .serializers import BookmarkSerializer, CommentSerializer, PollSerializer, PushSubscriptionSerializer
import jwt
import datetime
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import NewsletterSubscriber
from core.tasks import send_async_email

# Baaki imports jo pehle se hain wo waise hi rahenge...

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    
    # --- NAYA CODE YAHAN SE START HAI ---
    def get_permissions(self):
        # 'list' aur 'retrieve' (comments dekhna) sabke liye allow hai
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        # Comment create, update ya delete karne ke liye login (IsAuthenticated) hona zaroori hai
        return [permissions.IsAuthenticated()]
    # --- NAYA CODE YAHAN END HAI ---
    
    def get_queryset(self):
        # Agar URL mein article_id pass kiya hai, toh sirf uske comments laaye
        article_id = self.request.query_params.get('article_id')
        queryset = Comment.objects.filter(is_active=True).order_by('-created_at')
        if article_id:
            queryset = queryset.filter(article_id=article_id)
        return queryset

    def perform_create(self, serializer):
        # Comment banane wale user ko automatically set karein
        serializer.save(user=self.request.user)

class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated] # Sirf logged in users

    def get_queryset(self):
        # Sirf current logged-in user ke saved articles return karein
        return Bookmark.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



def send_email_in_background(subject, message, recipient_list, html_message=None):
    """Background mein email bhejne ka helper function"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
            html_message=html_message
        )
    except Exception as e:
        print(f"Email sending error: {e}")



class SubscribeNewsletterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
        
        if not created and subscriber.is_active:
            return Response({"message": "You are already subscribed!"}, status=status.HTTP_200_OK)
        
        subscriber.is_active = True
        subscriber.save()

        # ================== NAYA CODE: WELCOME EMAIL ==================
        if created or subscriber.is_active:
            subject = "🎉 Welcome to Forex Times - Stay Updated!"
            message = "Thank you for subscribing to Forex Times! You will now receive our daily top stories and breaking news alerts."
            
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
                    <h2>Welcome to Forex Times! 📰</h2>
                    <p>Hi there,</p>
                    <p>Thank you for subscribing! You are now part of our community. We promise to bring you the most accurate, fast, and reliable news directly to your inbox.</p>
                    <p><strong>What to expect:</strong></p>
                    <ul>
                        <li>🚨 Instant Breaking News Alerts</li>
                        <li>🌙 Daily Night Digest (Top stories of the day)</li>
                        <li>⭐ Weekend Editor's Special</li>
                    </ul>
                    <a href="{settings.FRONTEND_URL}/index.html" class="btn" style="color: white;">Read Latest News Now</a>
                    
                    <div class="footer">
                        If you ever wish to stop receiving emails, you can <a href="{settings.FRONTEND_URL}/unsubscribe.html?email={email}">unsubscribe here</a>.
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

    def post(self, request):
        token = request.data.get('token')
        email = request.data.get('email')

        # === 1. CONFIRM UNSUBSCRIBE LOGIC (Agar request mein token aaya hai) ===
        if token:
            try:
                # Token verify aur decode karein
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                
                if payload.get('type') != 'unsubscribe':
                    raise jwt.InvalidTokenError
                
                sub_email = payload.get('email')
                subscriber = NewsletterSubscriber.objects.get(email=sub_email)
                
                # User ko inactive mark karein
                subscriber.is_active = False
                subscriber.save()
                
                return Response({"message": "You have been successfully unsubscribed."})
                
            except jwt.ExpiredSignatureError:
                return Response({"error": "The unsubscribe link has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
            except (jwt.InvalidTokenError, NewsletterSubscriber.DoesNotExist):
                return Response({"error": "Invalid token or subscriber not found."}, status=status.HTTP_400_BAD_REQUEST)

        # === 2. REQUEST UNSUBSCRIBE LOGIC (Agar request mein email aaya hai) ===
        if email:
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
                
                # Unsubscribe Link banayein
                unsub_link = f"{settings.FRONTEND_URL}/unsubscribe.html?token={unsub_token}"
                
                # Email Bhejein
                subject = "Confirm Unsubscribe - Forex Times"
                message = f"Please click the following link to confirm your unsubscription: {unsub_link}"
                
                html_content = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h2 style="color: #d32f2f;">Confirm Unsubscribe</h2>
                    <p>We received a request to unsubscribe this email from Forex Times alerts.</p>
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

    @method_decorator(cache_page(60))
    def get(self, request):
        poll = Poll.objects.filter(is_active=True).first()
        if poll:
            return Response(PollSerializer(poll).data)
        return Response({"error": "No active poll found"}, status=status.HTTP_404_NOT_FOUND)

class VotePollView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, option_id):
        try:
            option = PollOption.objects.get(id=option_id)
            option.votes += 1
            option.save()
            return Response({"message": "Vote successfully counted!", "votes": option.votes})
        except PollOption.DoesNotExist:
            return Response({"error": "Option not found"}, status=status.HTTP_404_NOT_FOUND)
        



class SavePushSubscriptionView(APIView):
    permission_classes = [permissions.AllowAny]

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
