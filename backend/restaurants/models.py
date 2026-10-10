from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg


class Restaurant(models.Model):
    name = models.CharField("Название", max_length=150)
    logo = models.ImageField("Логотип", upload_to="restaurants/logos/", blank=True, null=True)
    address = models.CharField("Адрес", max_length=255)
    description = models.TextField("Описание", blank=True)
    delivery_time = models.PositiveIntegerField(
        "Время доставки (мин)", validators=[MinValueValidator(1)]
    )
    min_order_price = models.DecimalField(
        "Минимальная сумма заказа", max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )
    is_open = models.BooleanField("Открыт", default=True)

    class Meta:
        verbose_name = "Ресторан"
        verbose_name_plural = "Рестораны"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_avg_rating(self):
        """Средний рейтинг (0.0, если отзывов нет).

        Если queryset был аннотирован `avg_rating` (см. RestaurantViewSet),
        значение берётся из аннотации — без дополнительного запроса к БД.
        """
        annotated = getattr(self, "avg_rating", None)
        if annotated is not None:
            return round(float(annotated), 2)
        value = self.reviews.aggregate(avg=Avg("stars"))["avg"]
        return round(float(value), 2) if value is not None else 0.0


class MenuCategory(models.Model):
    name = models.CharField("Название", max_length=100)
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="categories", verbose_name="Ресторан"
    )

    class Meta:
        verbose_name = "Категория меню"
        verbose_name_plural = "Категории меню"
        ordering = ["restaurant", "name"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "name"], name="uniq_category_per_restaurant")
        ]

    def __str__(self):
        return f"{self.restaurant.name} — {self.name}"


class MenuItem(models.Model):
    name = models.CharField("Название", max_length=150)
    price = models.DecimalField(
        "Цена", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    description = models.TextField("Описание", blank=True)
    photo = models.ImageField("Фото", upload_to="menu/photos/", blank=True, null=True)
    weight = models.PositiveIntegerField("Вес (г)", validators=[MinValueValidator(1)])
    is_available = models.BooleanField("Доступно", default=True)
    category = models.ForeignKey(
        MenuCategory, on_delete=models.CASCADE, related_name="items", verbose_name="Категория"
    )

    class Meta:
        verbose_name = "Блюдо"
        verbose_name_plural = "Блюда"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name

    @property
    def restaurant(self):
        return self.category.restaurant


class RestaurantReview(models.Model):
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="reviews", verbose_name="Ресторан"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews",
        verbose_name="Пользователь",
    )
    stars = models.PositiveSmallIntegerField(
        "Оценка", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField("Комментарий", blank=True)
    created_date = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_date"]
        constraints = [
            models.UniqueConstraint(fields=["restaurant", "user"], name="uniq_review_per_user_restaurant"),
            models.CheckConstraint(
                condition=models.Q(stars__gte=1, stars__lte=5), name="review_stars_1_5"
            ),
        ]

    def __str__(self):
        return f"{self.restaurant.name}: {self.stars}★ от {self.user}"
