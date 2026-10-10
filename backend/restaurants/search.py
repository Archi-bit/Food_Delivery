"""Unicode-aware DRF search for local SQLite; PostgreSQL uses native ILIKE."""
from django.db import connections
from django.db.backends.signals import connection_created
from django.db.models import CharField, TextField, Transform
from django.dispatch import receiver
from rest_framework.filters import SearchFilter


@receiver(connection_created, dispatch_uid="restaurants.sqlite_unicode_casefold")
def register_sqlite_casefold(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        connection.connection.create_function(
            "FOOD_UNICODE_CASEFOLD", 1,
            lambda value: value.casefold() if value is not None else None,
            deterministic=True,
        )


@CharField.register_lookup
@TextField.register_lookup
class UnicodeCasefold(Transform):
    lookup_name = "unicode_casefold"
    function = "FOOD_UNICODE_CASEFOLD"


class UnicodeSearchFilter(SearchFilter):
    """Keep DRF terms, escaping and pagination, folding Cyrillic in SQLite.

    SQLite's built-in LIKE and LOWER only handle ASCII case. Fold both sides
    with Python Unicode rules inside the database rather than fetching all rows.
    """

    def filter_queryset(self, request, queryset, view):
        fields = self.get_search_fields(view, request) or []
        self.fold_unicode = (
            connections[queryset.db].vendor == "sqlite"
            and all(not field.startswith(tuple(self.lookup_prefixes)) and "__" not in field for field in fields)
        )
        return super().filter_queryset(request, queryset, view)

    def get_search_terms(self, request):
        terms = super().get_search_terms(request)
        return [term.casefold() for term in terms] if getattr(self, "fold_unicode", False) else terms

    def construct_search(self, field_name, queryset):
        if getattr(self, "fold_unicode", False):
            return f"{field_name}__unicode_casefold__contains"
        return super().construct_search(field_name, queryset)
