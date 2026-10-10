from django.db.models import Avg, Count, FloatField, Prefetch
from django.db.models.functions import Coalesce
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.response import Response

from users.permissions import IsOwnerOrStaffOrReadOnly, IsStaffOrReadOnly

from .filters import MenuItemFilter, RestaurantFilter, ReviewFilter
from .models import MenuCategory, MenuItem, Restaurant, RestaurantReview
from .serializers import (
    MenuCategoryReadSerializer,
    MenuCategoryWriteSerializer,
    MenuItemReadSerializer,
    MenuItemWriteSerializer,
    RestaurantDetailSerializer,
    RestaurantListSerializer,
    RestaurantWriteSerializer,
    ReviewReadSerializer,
    ReviewWriteSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=["restaurants"],
        summary="Список ресторанов",
        description="Доступно всем. Фильтры: `is_open`, `max_delivery_time`, `food_category`; поиск `search` по названию и описанию без учёта регистра (включая кириллицу); "
        "сортировка `ordering` по `avg_rating`, `delivery_time`, `min_order_price`, `name` "
        "(`-avg_rating` — от лучших к худшим).",
        parameters=[
            OpenApiParameter("ordering", OpenApiTypes.STR, description="Например: `-avg_rating`"),
        ],
    ),
    retrieve=extend_schema(tags=["restaurants"], summary="Ресторан с категориями и блюдами"),
    create=extend_schema(tags=["restaurants"], summary="Создать ресторан (staff)"),
    update=extend_schema(tags=["restaurants"], summary="Изменить ресторан (staff)"),
    partial_update=extend_schema(tags=["restaurants"], summary="Частично изменить ресторан (staff)"),
    destroy=extend_schema(tags=["restaurants"], summary="Удалить ресторан (staff)"),
)
class RestaurantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrReadOnly]
    filterset_class = RestaurantFilter
    search_fields = ["name", "description"]
    ordering_fields = ["avg_rating", "delivery_time", "min_order_price", "name"]
    ordering = ["name"]

    def get_queryset(self):
        qs = Restaurant.objects.annotate(
            avg_rating=Coalesce(Avg("reviews__stars"), 0.0, output_field=FloatField()),
            reviews_count=Count("reviews", distinct=True),
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related(
                Prefetch("categories", queryset=MenuCategory.objects.prefetch_related("items"))
            )
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RestaurantDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return RestaurantWriteSerializer
        return RestaurantListSerializer


@extend_schema_view(
    list=extend_schema(tags=["menu"], summary="Список категорий меню"),
    retrieve=extend_schema(tags=["menu"], summary="Категория с блюдами"),
    create=extend_schema(tags=["menu"], summary="Создать категорию (staff)"),
    update=extend_schema(tags=["menu"], summary="Изменить категорию (staff)"),
    partial_update=extend_schema(tags=["menu"], summary="Частично изменить категорию (staff)"),
    destroy=extend_schema(tags=["menu"], summary="Удалить категорию (staff)"),
)
class MenuCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrReadOnly]
    queryset = MenuCategory.objects.select_related("restaurant").prefetch_related("items")
    filterset_fields = ["restaurant"]
    search_fields = ["name"]
    ordering_fields = ["name"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MenuCategoryWriteSerializer
        return MenuCategoryReadSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["menu"],
        summary="Список блюд",
        description="Фильтры: `category`, `restaurant`, `is_available`, `min_price`, `max_price`; "
        "поиск `search` по названию/описанию; сортировка `ordering=price` или `-price`.",
    ),
    retrieve=extend_schema(tags=["menu"], summary="Блюдо"),
    create=extend_schema(
        tags=["menu"],
        summary="Создать блюдо (staff)",
        examples=[
            OpenApiExample(
                "Запрос",
                request_only=True,
                value={
                    "name": "Маргарита",
                    "price": "450.00",
                    "description": "Томаты, моцарелла, базилик",
                    "weight": 420,
                    "is_available": True,
                    "category": 1,
                },
            )
        ],
    ),
    update=extend_schema(tags=["menu"], summary="Изменить блюдо (staff)"),
    partial_update=extend_schema(tags=["menu"], summary="Частично изменить блюдо (staff)"),
    destroy=extend_schema(tags=["menu"], summary="Удалить блюдо (staff)"),
)
class MenuItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrReadOnly]
    queryset = MenuItem.objects.select_related("category__restaurant")
    filterset_class = MenuItemFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "name", "weight"]
    ordering = ["category", "name"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MenuItemWriteSerializer
        return MenuItemReadSerializer


@extend_schema_view(
    list=extend_schema(tags=["reviews"], summary="Отзывы (фильтр `restaurant`, `stars`)"),
    retrieve=extend_schema(tags=["reviews"], summary="Отзыв"),
    create=extend_schema(
        tags=["reviews"],
        summary="Оставить отзыв (авторизованный пользователь)",
        examples=[
            OpenApiExample(
                "Запрос", request_only=True,
                value={"restaurant": 1, "stars": 5, "comment": "Очень вкусно и быстро!"},
            )
        ],
    ),
    update=extend_schema(tags=["reviews"], summary="Изменить свой отзыв"),
    partial_update=extend_schema(tags=["reviews"], summary="Частично изменить свой отзыв"),
    destroy=extend_schema(tags=["reviews"], summary="Удалить свой отзыв"),
)
class RestaurantReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerOrStaffOrReadOnly]
    queryset = RestaurantReview.objects.select_related("user", "restaurant")
    filterset_class = ReviewFilter
    ordering_fields = ["created_date", "stars"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ReviewWriteSerializer
        return ReviewReadSerializer

    def create(self, request, *args, **kwargs):
        # Ответ после создания — в «читаемом» виде
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(ReviewReadSerializer(review).data, status=status.HTTP_201_CREATED)
