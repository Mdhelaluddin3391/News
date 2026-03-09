from rest_framework import viewsets, permissions
from .models import Bookmark, Comment
from .serializers import BookmarkSerializer, CommentSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import NewsletterSubscriber
from .models import Poll, PollOption
from .serializers import PollSerializer
from rest_framework import permissions, status

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


class SubscribeNewsletterView(APIView):
    permission_classes = [permissions.AllowAny] # Koi bhi subscribe kar sakta hai

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check karein agar email pehle se hai
        subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
        
        if not created and subscriber.is_active:
            return Response({"message": "You are already subscribed!"}, status=status.HTTP_200_OK)
        
        # Agar user ne pehle unsubscribe kiya tha, toh wapas active kar do
        subscriber.is_active = True
        subscriber.save()
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

    def get(self, request):
        # Sirf wo poll bhejo jo 'is_active=True' hai
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