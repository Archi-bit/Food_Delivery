"""Persistent browser sessions; existing JWT endpoints remain compatible."""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from drf_spectacular.utils import extend_schema

from .serializers import RegisterSerializer, UserSerializer


class BrowserSessionSerializer(serializers.Serializer):
    access = serializers.CharField(allow_null=True, read_only=True)
    user = UserSerializer(allow_null=True, read_only=True)


class BrowserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class CSRFSerializer(serializers.Serializer):
    csrf_token = serializers.CharField(read_only=True)


def session_data(user, request):
    if not user.is_authenticated:
        return {"access": None, "user": None}
    return {"access": str(AccessToken.for_user(user)),
            "user": UserSerializer(user, context={"request": request}).data}


class UncachedAPIView(APIView):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class CSRFView(UncachedAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["auth"], responses=CSRFSerializer)
    def get(self, request):
        return Response({"csrf_token": get_token(request._request)})


class BrowserSessionView(UncachedAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(tags=["auth"], responses=BrowserSessionSerializer)
    def get(self, request):
        return Response(session_data(request.user, request))


class CSRFProtectedView(UncachedAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Explicit enforcement also protects anonymous login and registration.
        SessionAuthentication().enforce_csrf(request)


class BrowserLoginView(CSRFProtectedView):
    @extend_schema(tags=["auth"], request=BrowserLoginSerializer,
                   responses=BrowserSessionSerializer)
    def post(self, request):
        serializer = BrowserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request=request._request, **serializer.validated_data)
        if user is None:
            raise AuthenticationFailed("Неверное имя пользователя или пароль.")
        login(request._request, user)
        request._request.session.set_expiry(7 * 24 * 60 * 60)
        return Response(session_data(user, request))


class BrowserRegisterView(CSRFProtectedView):
    @extend_schema(tags=["auth"], request=RegisterSerializer,
                   responses={201: BrowserSessionSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
        request._request.session.set_expiry(7 * 24 * 60 * 60)
        return Response(session_data(user, request), status=status.HTTP_201_CREATED)


class BrowserLogoutView(CSRFProtectedView):
    @extend_schema(tags=["auth"], request=None, responses={204: None})
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)
