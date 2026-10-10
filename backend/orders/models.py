from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from restaurants.models import MenuItem, Restaurant


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart", verbose_name="Пользователь"
    )

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Корзина {self.user}"

    def get_total_price(self):
        return sum(
            (ci.item.price * ci.quantity for ci in self.items.all()), Decimal("0.00")
        )


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", verbose_name="Корзина")
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="cart_items", verbose_name="Блюдо")
    quantity = models.PositiveIntegerField("Количество", default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзины"
        constraints = [models.UniqueConstraint(fields=["cart", "item"], name="uniq_item_per_cart")]

    def __str__(self):
        return f"{self.item.name} × {self.quantity}"

    def get_subtotal(self):
        return self.item.price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        PREPARING = "preparing", "Готовится"
        ON_WAY = "on_way", "В пути"
        DELIVERED = "delivered", "Доставлен"

    # Допустимый порядок прохождения статусов
    STATUS_FLOW = [Status.NEW, Status.PREPARING, Status.ON_WAY, Status.DELIVERED]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders", verbose_name="Пользователь"
    )
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.PROTECT, related_name="orders", verbose_name="Ресторан"
    )
    items = models.ManyToManyField(
        MenuItem, through="OrderItem", related_name="orders", verbose_name="Блюда"
    )
    delivery_address = models.CharField("Адрес доставки", max_length=255)
    status = models.CharField("Статус", max_length=20, choices=Status.choices, default=Status.NEW)
    created_date = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_date"]

    def __str__(self):
        return f"Заказ #{self.pk} ({self.get_status_display()})"

    def get_total_price(self):
        """Сумма по зафиксированным ценам OrderItem.price (не зависит от текущей цены блюда)."""
        return sum((oi.price * oi.quantity for oi in self.order_items.all()), Decimal("0.00"))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items", verbose_name="Заказ")
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name="order_items", verbose_name="Блюдо")
    quantity = models.PositiveIntegerField("Количество", default=1, validators=[MinValueValidator(1)])
    price = models.DecimalField("Цена на момент заказа", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return f"{self.item.name} × {self.quantity}"


class DemoPayment(models.Model):
    """Учебная имитация, никогда не является банковской транзакцией."""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="demo_payment")
    success = models.BooleanField(default=False)
