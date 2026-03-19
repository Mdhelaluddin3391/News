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
            subject = "🎉 Welcome to NewsHub - Stay Updated!"
            message = "Thank you for subscribing to NewsHub! You will now receive our daily top stories and breaking news alerts."
            
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
                    <h2>Welcome to NewsHub! 📰</h2>
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
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email)
            subscriber.is_active = False # Email delete nahi karenge, bas inactive kar denge
            subscriber.save()
            return Response({"message": "Successfully unsubscribed."})
        except NewsletterSubscriber.DoesNotExist:
            return Response({"error": "This email is not registered in our subscriber list."}, status=status.HTTP_404_NOT_FOUND)
        
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
