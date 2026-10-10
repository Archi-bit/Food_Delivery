from users.validators import validate_image
from users.validators import validate_image
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import MenuCategory, MenuItem, Restaurant, RestaurantReview


# ───────────── Блюда ─────────────
class MenuItemReadSerializer(serializers.ModelSerializer):
    """Чтение блюда: категория вложена, внутри — краткая информация о ресторане."""

    category = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = ("id", "name", "price", "description", "photo", "weight", "is_available", "category")

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "restaurant": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                },
            },
        }
    )
    def get_category(self, obj):
        return {
            "id": obj.category_id,
            "name": obj.category.name,
            "restaurant": {
                "id": obj.category.restaurant_id,
                "name": obj.category.restaurant.name,
            },
        }


class MenuItemWriteSerializer(serializers.ModelSerializer):
    def validate_photo(self, value):
        return validate_image(value)

    """Запись блюда: категория передаётся по ID."""

    category = serializers.PrimaryKeyRelatedField(queryset=MenuCategory.objects.all())

    class Meta:
        model = MenuItem
        fields = ("id", "name", "price", "description", "photo", "weight", "is_available", "category")

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть больше нуля.")
        return value


class MenuItemBriefSerializer(serializers.ModelSerializer):
    """Блюдо внутри вложенных структур (категория → ресторан, корзина, заказ)."""

    class Meta:
        model = MenuItem
        fields = ("id", "name", "price", "photo", "weight", "is_available")


# ───────────── Категории ─────────────
class MenuCategoryReadSerializer(serializers.ModelSerializer):
    items = MenuItemBriefSerializer(many=True, read_only=True)

    class Meta:
        model = MenuCategory
        fields = ("id", "name", "restaurant", "items")


class MenuCategoryWriteSerializer(serializers.ModelSerializer):
    restaurant = serializers.PrimaryKeyRelatedField(queryset=Restaurant.objects.all())

    class Meta:
        model = MenuCategory
        fields = ("id", "name", "restaurant")


# ───────────── Рестораны ─────────────
class RestaurantListSerializer(serializers.ModelSerializer):
    avg_rating = serializers.SerializerMethodField()
    reviews_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "logo", "address", "description", "delivery_time",
            "min_order_price", "is_open", "avg_rating", "reviews_count",
        )

    def get_avg_rating(self, obj) -> float:
        return obj.get_avg_rating()


class RestaurantDetailSerializer(RestaurantListSerializer):
    """Детальная карточка: ресторан → категории → блюда."""

    categories = MenuCategoryReadSerializer(many=True, read_only=True)

    class Meta(RestaurantListSerializer.Meta):
        fields = RestaurantListSerializer.Meta.fields + ("categories",)


class RestaurantWriteSerializer(serializers.ModelSerializer):
    def validate_logo(self, value):
        return validate_image(value)

    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "logo", "address", "description",
            "delivery_time", "min_order_price", "is_open",
        )


# ───────────── Отзывы ─────────────
class ReviewReadSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = RestaurantReview
        fields = ("id", "restaurant", "user", "stars", "comment", "created_date")


class ReviewWriteSerializer(serializers.ModelSerializer):
    restaurant = serializers.PrimaryKeyRelatedField(queryset=Restaurant.objects.all())
    stars = serializers.IntegerField(min_value=1, max_value=5)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = RestaurantReview
        fields = ("id", "restaurant", "user", "stars", "comment")
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=RestaurantReview.objects.all(),
                fields=("restaurant", "user"),
                message="Вы уже оставили отзыв на этот ресторан.",
            )
        ]

    def validate_restaurant(self, value):
        if self.instance and self.instance.restaurant_id != value.id:
            raise serializers.ValidationError("Нельзя перенести отзыв на другой ресторан.")
        return value
