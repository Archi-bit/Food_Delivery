from users.validators import validate_image
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    def validate_avatar(self, value):
        return validate_image(value)

    """Профиль текущего пользователя (чтение и частичное обновление)."""

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "delivery_address", "phone_number", "avatar", "date_register",
            "is_staff",
        )
        read_only_fields = ("id", "username", "date_register", "is_staff")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = (
            "id", "username", "email", "password", "password2",
            "first_name", "last_name", "delivery_address", "phone_number",
        )
        extra_kwargs = {"email": {"required": True, "allow_blank": False}}

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Пароли не совпадают."})
        candidate = User(**{k: v for k, v in attrs.items() if k != "password"})
        validate_password(attrs["password"], user=candidate)
        return attrs

    def create(self, validated_data):
        # create_user хэширует пароль
        return User.objects.create_user(**validated_data)

    def to_representation(self, instance):
        data = UserSerializer(instance, context=self.context).data
        refresh = RefreshToken.for_user(instance)
        return {
            "user": data,
            "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
        }
