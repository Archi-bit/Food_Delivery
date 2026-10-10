from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from restaurants.models import MenuItem
from restaurants.serializers import MenuItemBriefSerializer

from .models import Cart, CartItem, Order, OrderItem


def validate_item_available(item: MenuItem):
    if not item.is_available:
        raise serializers.ValidationError(f"Блюдо «{item.name}» сейчас недоступно.")
    return item


# ───────────── Корзина ─────────────
class CartItemReadSerializer(serializers.ModelSerializer):
    item = MenuItemBriefSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ("id", "item", "quantity", "subtotal")

    def get_subtotal(self, obj) -> str:
        return str(obj.get_subtotal())


class CartSerializer(serializers.ModelSerializer):
    items = CartItemReadSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "total_price")

    def get_total_price(self, obj) -> str:
        return str(obj.get_total_price())


class CartItemAddSerializer(serializers.Serializer):
    """Добавление блюда в корзину по ID. Если блюдо уже есть — количество увеличивается."""

    item = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.select_related("category__restaurant")
    )
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)

    def validate_item(self, item):
        return validate_item_available(item)

    def validate(self, attrs):
        cart = self.context["cart"]
        item = attrs["item"]
        other = cart.items.exclude(item=item).select_related("item__category").first()
        if other and other.item.category.restaurant_id != item.category.restaurant_id:
            raise serializers.ValidationError(
                "В корзине уже есть блюда другого ресторана. Очистите корзину или оформите заказ."
            )
        existing = cart.items.filter(item=item).first()
        total = (existing.quantity if existing else 0) + attrs["quantity"]
        if total > 99:
            raise serializers.ValidationError({"quantity": "Максимум 99 порций одного блюда."})
        return attrs


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=99)


# ───────────── Заказы ─────────────
class OrderItemReadSerializer(serializers.ModelSerializer):
    item = MenuItemBriefSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ("id", "item", "quantity", "price", "subtotal")

    def get_subtotal(self, obj) -> str:
        return str(obj.price * obj.quantity)


class OrderReadSerializer(serializers.ModelSerializer):
    order_items = OrderItemReadSerializer(many=True, read_only=True)
    restaurant = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_price = serializers.SerializerMethodField()
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "user", "restaurant", "delivery_address", "status", "status_display",
            "created_date", "order_items", "total_price",
        )

    @extend_schema_field({"type": "object", "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}})
    def get_restaurant(self, obj):
        return {"id": obj.restaurant_id, "name": obj.restaurant.name}

    def get_total_price(self, obj) -> str:
        return str(obj.get_total_price())


class CheckoutSerializer(serializers.Serializer):
    """Оформление заказа из корзины. Адрес необязателен — берётся из профиля."""

    delivery_address = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        user = self.context["request"].user
        address = (attrs.get("delivery_address") or user.delivery_address or "").strip()
        if not address:
            raise serializers.ValidationError(
                {"delivery_address": "Укажите адрес доставки (в запросе или в профиле)."}
            )
        attrs["delivery_address"] = address
        return attrs


class OrderStatusSerializer(serializers.ModelSerializer):
    """Смена статуса (только staff). Статусы идут строго вперёд: new → preparing → on_way → delivered."""

    class Meta:
        model = Order
        fields = ("status",)

    def validate_status(self, value):
        flow = [s.value for s in Order.STATUS_FLOW]
        current = self.instance.status
        if flow.index(value) <= flow.index(current):
            raise serializers.ValidationError(
                f"Нельзя перевести заказ из «{current}» в «{value}»: статус можно только продвигать вперёд."
            )
        return value
