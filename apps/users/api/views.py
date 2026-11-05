from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from .throttles import AuthRateThrottle
from apps.users.api.serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    RegisterSerializer,
    UserSerializer,
)
from apps.users.models import User


class RegisterAPIView(generics.CreateAPIView):
    throttle_classes = [AuthRateThrottle]
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user, context={"request": request}).data

        return Response(
            {
                **user_data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    throttle_classes = [AuthRateThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user, context={"request": request}).data

        return Response(
            {
                **user_data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class RefreshAPIView(TokenRefreshView):
    permission_classes = [AllowAny]


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # پشتیبانی همزمان از کلیدهای refresh و refresh_token
        refresh_token = request.data.get("refresh") or request.data.get("refresh_token")

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                # جلوگیری از کرش کردن با خطای 500 در صورت ارسال توکن نامعتبر یا منقضی
                pass

        return Response(status=status.HTTP_204_NO_CONTENT)


class MeAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ProfilePictureAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        picture = request.data.get("profile_picture")
        if not picture:
            return Response(
                {"profile_picture": "This file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        user.profile_picture = picture
        user.save(update_fields=["profile_picture"])

        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        user = request.user
        if user.profile_picture:
            user.profile_picture.delete(save=True)

        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class PasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Password changed."},
            status=status.HTTP_200_OK,
        )
    def post(self, request):
        return self.patch(request)


class UserSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        mobile = request.query_params.get("mobile")
        if not mobile:
            return Response(
                {"mobile": "This query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(mobile=mobile).first()
        if user is None:
            return Response(
                "User not found.",
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

