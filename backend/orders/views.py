from django.db import transaction
from django.conf import settings
from rest_framework.exceptions import NotFound
from .demo import DemoPaymentSerializer, DemoPaymentResultSerializer
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Cart, CartItem, Order, OrderItem, DemoPayment
from .serializers import (
    CartItemAddSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
    CheckoutSerializer,
    OrderReadSerializer,
    OrderStatusSerializer,
)


def get_user_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def cart_queryset():
    return Cart.objects.prefetch_related("items__item__category__restaurant")


class CartViewSet(viewsets.GenericViewSet):
    """Корзина текущего пользователя. Чужие корзины недоступны by design — URL не содержит ID корзины."""

    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    queryset = Cart.objects.none()  # для drf-spectacular; реальная выборка — по request.user
    pagination_class = None

    def _cart_response(self, request, code=status.HTTP_200_OK):
        cart = cart_queryset().get(pk=get_user_cart(request.user).pk)
        return Response(CartSerializer(cart, context={"request": request}).data, status=code)

    @extend_schema(tags=["cart"], summary="Моя корзина", responses=CartSerializer)
    def list(self, request):
        return self._cart_response(request)

    @extend_schema(
        tags=["cart"],
        summary="Добавить блюдо в корзину",
        request=CartItemAddSerializer,
        responses={201: CartSerializer},
        examples=[OpenApiExample("Запрос", request_only=True, value={"item": 3, "quantity": 2})],
    )
    @action(detail=False, methods=["post"], url_path="items")
    @transaction.atomic
    def add_item(self, request):
        cart = Cart.objects.select_for_update().get_or_create(user=request.user)[0]
        serializer = CartItemAddSerializer(data=request.data, context={"cart": cart, "request": request})
        serializer.is_valid(raise_exception=True)
        item = serializer.validated_data["item"]
        qty = serializer.validated_data["quantity"]
        cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item, defaults={"quantity": qty})
        if not created:
            cart_item.quantity += qty
            cart_item.save(update_fields=["quantity"])
        return self._cart_response(request, status.HTTP_201_CREATED)

    @extend_schema(
        tags=["cart"],
        methods=["PATCH"],
        summary="Изменить количество позиции корзины",
        request=CartItemUpdateSerializer,
        responses=CartSerializer,
        examples=[OpenApiExample("Запрос", request_only=True, value={"quantity": 3})],
    )
    @extend_schema(
        tags=["cart"],
        methods=["DELETE"],
        summary="Удалить позицию из корзины",
        responses={200: CartSerializer},
    )
    @action(detail=False, methods=["patch", "delete"], url_path=r"items/(?P<cart_item_id>\d+)")
    @transaction.atomic
    def item_detail(self, request, cart_item_id=None):
        cart = Cart.objects.select_for_update().get_or_create(user=request.user)[0]
        try:
            cart_item = cart.items.select_related("item").get(pk=cart_item_id)
        except CartItem.DoesNotExist:
            return Response({"detail": "Позиция не найдена в вашей корзине."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            cart_item.delete()
        else:
            serializer = CartItemUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if not cart_item.item.is_available:
                raise ValidationError({"item": f"Блюдо «{cart_item.item.name}» сейчас недоступно."})
            cart_item.quantity = serializer.validated_data["quantity"]
            cart_item.save(update_fields=["quantity"])
        return self._cart_response(request)

    @extend_schema(tags=["cart"], summary="Очистить корзину", request=None, responses=CartSerializer)
    @action(detail=False, methods=["post"], url_path="clear")
    @transaction.atomic
    def clear(self, request):
        Cart.objects.select_for_update().get_or_create(user=request.user)[0].items.all().delete()
        return self._cart_response(request)


@extend_schema_view(
    list=extend_schema(
        tags=["orders"],
        summary="Мои заказы (для staff — все)",
        description="Фильтр `status`; сортировка `ordering=created_date` / `-created_date`.",
    ),
    retrieve=extend_schema(tags=["orders"], summary="Заказ"),
    destroy=extend_schema(tags=["orders"], summary="Удалить заказ (staff)"),
)
class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrderReadSerializer
    filterset_fields = ["status", "restaurant"]
    ordering_fields = ["created_date", "status"]
    ordering = ["-created_date"]

    def get_permissions(self):
        if self.action in ("destroy", "set_status"):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Order.objects.select_related("restaurant", "user").prefetch_related("order_items__item")
        if getattr(self, "swagger_fake_view", False):  # генерация схемы drf-spectacular
            return qs.none()
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(user=user)

    @extend_schema(
        tags=["orders"],
        summary="Оформить заказ из корзины",
        description=(
            "Превращает корзину пользователя в заказ: позиции переносятся в `OrderItem` с фиксацией "
            "текущей цены, после чего корзина очищается. Проверяется: корзина не пуста, все блюда "
            "доступны, ресторан открыт, сумма не меньше `min_order_price` ресторана."
        ),
        request=CheckoutSerializer,
        responses={
            201: OrderReadSerializer,
            400: OpenApiResponse(description="Пустая корзина / блюдо недоступно / сумма меньше минимальной"),
        },
        examples=[
            OpenApiExample(
                "Запрос", request_only=True, value={"delivery_address": "Бишкек, пр. Чуй 100, кв. 12"}
            )
        ],
    )
    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        serializer = CheckoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        address = serializer.validated_data["delivery_address"]

        with transaction.atomic():
            cart = Cart.objects.select_for_update().get_or_create(user=request.user)[0]
            cart_items = list(cart.items.select_related("item__category__restaurant"))
            if not cart_items:
                raise ValidationError({"detail": "Корзина пуста."})

            unavailable = [ci.item.name for ci in cart_items if not ci.item.is_available]
            if unavailable:
                raise ValidationError(
                    {"items": f"Недоступные блюда: {', '.join(unavailable)}. Удалите их из корзины."}
                )

            restaurants = {ci.item.category.restaurant_id for ci in cart_items}
            if len(restaurants) != 1:
                raise ValidationError({"detail": "Заказ может содержать блюда только одного ресторана."})
            restaurant = cart_items[0].item.category.restaurant

            if not restaurant.is_open:
                raise ValidationError({"detail": f"Ресторан «{restaurant.name}» сейчас закрыт."})

            total = sum(ci.item.price * ci.quantity for ci in cart_items)
            if total < restaurant.min_order_price:
                raise ValidationError(
                    {
                        "detail": f"Сумма заказа {total} меньше минимальной для ресторана "
                        f"«{restaurant.name}»: {restaurant.min_order_price}."
                    }
                )

            order = Order.objects.create(user=request.user, restaurant=restaurant, delivery_address=address)
            OrderItem.objects.bulk_create(
                [
                    OrderItem(order=order, item=ci.item, quantity=ci.quantity, price=ci.item.price)
                    for ci in cart_items
                ]
            )
            cart.items.all().delete()

        order = self.get_queryset().get(pk=order.pk)
        return Response(OrderReadSerializer(order, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["orders"],
        summary="Сменить статус заказа (staff)",
        request=OrderStatusSerializer,
        responses=OrderReadSerializer,
        examples=[OpenApiExample("Запрос", request_only=True, value={"status": "preparing"})],
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusSerializer(order, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrderReadSerializer(order, context={"request": request}).data)

    @extend_schema(request=DemoPaymentSerializer, responses=DemoPaymentResultSerializer)
    @action(detail=True, methods=["post"], url_path="demo-payment")
    def demo_payment(self, request, pk=None):
        if not settings.DEMO_MODE:
            raise NotFound()
        serializer = DemoPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            order = self.get_queryset().select_for_update(of=("self",)).get(pk=self.get_object().pk)
            payment, _ = DemoPayment.objects.get_or_create(order=order)
            if payment.success:
                return Response({"demo": True, "success": True})
            payment.success = serializer.validated_data["success"]
            payment.save()
        return Response({"demo": True, "success": payment.success})

    @extend_schema(request=None, responses=OrderReadSerializer)
    @action(detail=True, methods=["post"], url_path="demo-advance")
    def demo_advance(self, request, pk=None):
        if not settings.DEMO_MODE:
            raise NotFound()
        with transaction.atomic():
            order = self.get_queryset().select_for_update(of=("self",)).get(pk=self.get_object().pk)
            if not DemoPayment.objects.filter(order=order, success=True).exists():
                raise ValidationError({"detail": "Сначала выполните демонстрационную оплату."})
            flow = [s.value for s in Order.STATUS_FLOW]
            order.status = flow[min(flow.index(order.status) + 1, len(flow) - 1)]
            order.save(update_fields=["status"])
        return Response(OrderReadSerializer(order, context={"request": request}).data)
