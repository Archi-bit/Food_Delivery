from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    list_display = ("username", "email", "phone_number", "delivery_address", "is_staff", "date_register")
    list_filter = ("is_staff", "is_active", "date_register")
    search_fields = ("username", "email", "phone_number", "delivery_address")
    readonly_fields = ("date_register",)
    fieldsets = UserAdmin.fieldsets + (
        ("Доставка", {"fields": ("delivery_address", "phone_number", "avatar", "date_register")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Доставка", {"fields": ("email", "delivery_address", "phone_number")}),
    )
