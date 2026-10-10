from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r"^\+?\d{9,15}$",
    message="Телефон в формате +996555123456 (9–15 цифр, допускается ведущий +).",
)


class UserProfile(AbstractUser):
    """Пользователь сервиса: стандартный AbstractUser + данные для доставки."""

    delivery_address = models.CharField("Адрес доставки", max_length=255, blank=True)
    phone_number = models.CharField(
        "Телефон", max_length=16, blank=True, validators=[phone_validator]
    )
    avatar = models.ImageField("Аватар", upload_to="avatars/", blank=True, null=True)
    date_register = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username
