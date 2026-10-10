import django_filters
from django.db.models import Exists, OuterRef, Q

from .models import MenuItem, Restaurant, RestaurantReview


FOOD_CATEGORIES = {
    "pizza": ("Пицца", ("пицц", "pizza")),
    "lagman": ("Лагман", ("лагман", "lagman")),
    "manty": ("Манты", ("манты", "манти", "manty")),
    "salad": ("Салат", ("салат", "salad")),
    "desserts": ("Десерты", ("десерт", "dessert")),
}
FOOD_CHOICES = [(slug, label) for slug, (label, _) in FOOD_CATEGORIES.items()]


def food_match(value):
    """Match a menu category or dish name, including Cyrillic on SQLite.

    SQLite's icontains only folds ASCII, so include common Cyrillic cases.
    Desserts are matched by menu category, not by a single cake name.
    """
    query = Q()
    for term in FOOD_CATEGORIES[value][1]:
        for variant in {term, term.capitalize(), term.upper()}:
            query |= Q(name__icontains=variant) | Q(category__name__icontains=variant)
    return query


class RestaurantFilter(django_filters.FilterSet):
    max_delivery_time = django_filters.NumberFilter(field_name="delivery_time", lookup_expr="lte")
    food_category = django_filters.ChoiceFilter(choices=FOOD_CHOICES, method="filter_food")

    def filter_food(self, queryset, name, value):
        matches = MenuItem.objects.filter(
            category__restaurant_id=OuterRef("pk"), is_available=True,
        ).filter(food_match(value))
        # EXISTS preserves rating aggregates and does not duplicate restaurants
        # when several dishes match, so pagination remains correct.
        return queryset.filter(Exists(matches))

    class Meta:
        model = Restaurant
        fields = ["is_open", "max_delivery_time"]


class MenuItemFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    restaurant = django_filters.NumberFilter(field_name="category__restaurant_id")
    food_category = django_filters.ChoiceFilter(choices=FOOD_CHOICES, method="filter_food")

    def filter_food(self, queryset, name, value):
        return queryset.filter(food_match(value))

    class Meta:
        model = MenuItem
        fields = ["category", "is_available", "restaurant", "min_price", "max_price"]


class ReviewFilter(django_filters.FilterSet):
    class Meta:
        model = RestaurantReview
        fields = ["restaurant", "stars", "user"]
