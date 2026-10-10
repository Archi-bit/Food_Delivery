from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import RegisterSerializer, UserSerializer


@extend_schema(
    tags=["auth"],
    summary="Регистрация нового пользователя",
    description="Создаёт пользователя и сразу возвращает пару JWT-токенов.",
    examples=[
        OpenApiExample(
            "Запрос",
            request_only=True,
            value={
                "username": "aibek",
                "email": "aibek@example.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
                "phone_number": "+996555123456",
                "delivery_address": "Бишкек, ул. Токтогула 1, кв. 5",
            },
        )
    ],
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            self.get_serializer(user).data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["auth"], summary="Профиль текущего пользователя")
class MeView(generics.RetrieveUpdateAPIView):
    """GET — получить профиль, PATCH/PUT — изменить адрес, телефон, аватар и т.д."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user
