from django.contrib import admin
from django.db.models import Avg, FloatField
from django.db.models.functions import Coalesce

from .models import MenuCategory, MenuItem, Restaurant, RestaurantReview


class MenuCategoryInline(admin.TabularInline):
    model = MenuCategory
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "delivery_time", "min_order_price", "is_open", "avg_rating")
    list_filter = ("is_open",)
    search_fields = ("name", "address", "description")
    list_editable = ("is_open",)
    inlines = [MenuCategoryInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(avg_rating=Coalesce(Avg("reviews__stars"), 0.0, output_field=FloatField()))

    @admin.display(description="Рейтинг")
    def avg_rating(self, obj):
        return obj.get_avg_rating()


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant")
    list_filter = ("restaurant",)
    search_fields = ("name", "restaurant__name")


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "weight", "is_available")
    list_filter = ("is_available", "category__restaurant", "category")
    search_fields = ("name", "description", "category__name", "category__restaurant__name")
    list_editable = ("price", "is_available")
    list_select_related = ("category__restaurant",)


@admin.register(RestaurantReview)
class RestaurantReviewAdmin(admin.ModelAdmin):
    list_display = ("restaurant", "user", "stars", "created_date")
    list_filter = ("stars", "restaurant")
    search_fields = ("restaurant__name", "user__username", "comment")
    date_hierarchy = "created_date"
