from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
)


class RegisterView(views.APIView):
    """
    Registers a new user and automatically establishes their organization.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Issues JWT access and refresh tokens along with tenant context.
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileView(views.APIView):
    """
    Retrieves the currently authenticated user's profile and active organization roles.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)