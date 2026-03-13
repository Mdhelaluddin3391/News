from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
import jwt
import datetime
from .serializers import RegisterSerializer, UserSerializer
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        # Current logged-in user ki profile return karega
        return self.request.user

class ForgotPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            
            # Generate a secure JWT token valid for 15 minutes
            payload = {
                'user_id': user.id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
                'type': 'reset_password'
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            # Create the reset link
            reset_link = f"{settings.FRONTEND_URL}/reset-password.html?token={token}"

            # Send Email

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }}
                    .email-container {{ max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
                    .header {{ background-color: #1a365d; padding: 25px; text-align: center; }}
                    .header h1 {{ margin: 0; color: #ffffff; font-size: 24px; letter-spacing: 1px; }}
                    .content {{ padding: 35px; color: #334155; line-height: 1.6; font-size: 16px; text-align: center; }}
                    .content p {{ margin-bottom: 20px; }}
                    .btn {{ display: inline-block; background-color: #d32f2f; color: #ffffff; text-decoration: none; padding: 14px 30px; border-radius: 50px; font-weight: bold; font-size: 16px; margin: 10px 0; }}
                    .footer {{ background-color: #f1f5f9; padding: 20px; text-align: center; color: #64748b; font-size: 13px; border-top: 1px solid #e2e8f0; }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="header">
                        <h1>📰 NewsHub</h1>
                    </div>
                    <div class="content">
                        <h2 style="color: #1a365d;">Password Reset Request</h2>
                        <p>Hello <strong>{user.name}</strong>,</p>
                        <p>We received a request to reset your password. Click the button below to set a new password. This link is valid for <strong>15 minutes</strong>.</p>
                        
                        <a href="{reset_link}" class="btn" style="color: #ffffff;">Reset Password</a>
                        
                        <p style="margin-top: 30px; font-size: 14px; color: #94a3b8;">If you did not request this, please ignore this email. Your account is safe.</p>
                    </div>
                    <div class="footer">
                        &copy; 2026 NewsHub by Dharmanagar Live. All rights reserved.
                    </div>
                </div>
            </body>
            </html>
            """



            send_mail(
                subject='Password Reset Request - NewsHub',
                message=f'Hello {user.name},\n\nClick the link below to reset your password:\n{reset_link}', # Plain text as fallback
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
                html_message=html_content  # <--- NAYA PARAMETER
            )
        except User.DoesNotExist:
            pass

        return Response({"message": "If that email is registered, we have sent a reset link."})

class ResetPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        token = request.data.get('token')
        password = request.data.get('password')

        if not token or not password:
            return Response({"error": "Token and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            if payload.get('type') != 'reset_password':
                raise jwt.InvalidTokenError

            user = User.objects.get(id=payload['user_id'])
            user.set_password(password)
            user.save()

            return Response({"message": "Password reset successful."})

        except jwt.ExpiredSignatureError:
            return Response({"error": "The reset link has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)
        

class GoogleLoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Google token verify karein
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )

            email = idinfo['email']
            name = idinfo.get('name', 'Google User')
            picture = idinfo.get('picture', '')

            # Check karein ki user pehle se hai ya nahi
            user, created = User.objects.get_or_create(email=email)
            
            if created:
                # Naya user hai toh details save karein
                user.name = name
                user.role = 'subscriber'
                user.set_unusable_password() # Kyunki password Google handle kar raha hai
                user.save()

            # Generate JWT tokens for our app
            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            })

        except ValueError:
            # Invalid token
            return Response({"error": "Invalid Google Token"}, status=status.HTTP_400_BAD_REQUEST)