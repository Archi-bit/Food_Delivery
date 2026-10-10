from django.contrib import admin
from django import forms

from .models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ()
    raw_id_fields = ("item",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("item", "quantity", "price")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

    def clean_status(self):
        value = self.cleaned_data["status"]
        flow = [s.value for s in Order.STATUS_FLOW]
        if self.instance.pk and flow.index(value) < flow.index(self.instance.status):
            raise forms.ValidationError("Статус заказа нельзя возвращать назад.")
        return value



@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "items_count", "total")
    search_fields = ("user__username", "user__email")
    inlines = [CartItemInline]

    @admin.display(description="Позиций")
    def items_count(self, obj):
        return obj.items.count()

    @admin.display(description="Сумма")
    def total(self, obj):
        return obj.get_total_price()


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "item", "quantity")
    list_filter = ("item__category__restaurant",)
    search_fields = ("cart__user__username", "item__name")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    readonly_fields = ("user", "restaurant", "delivery_address", "created_date")
    list_select_related = ("user", "restaurant")

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("order_items")

    list_display = ("id", "user", "restaurant", "status", "total", "created_date")
    list_filter = ("status", "restaurant", "created_date")
    search_fields = ("id", "user__username", "delivery_address", "restaurant__name")
    list_editable = ("status",)
    date_hierarchy = "created_date"
    inlines = [OrderItemInline]

    @admin.display(description="Сумма")
    def total(self, obj):
        return obj.get_total_price()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    readonly_fields = ("order", "item", "quantity", "price")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ("order", "item", "quantity", "price")
    list_filter = ("order__status",)
    search_fields = ("item__name", "order__user__username")
