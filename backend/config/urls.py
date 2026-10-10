from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.http import JsonResponse
from django.db import connection

def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok", "demo_mode": settings.DEMO_MODE})

from orders.views import CartViewSet, OrderViewSet
from restaurants.views import (
    MenuCategoryViewSet,
    MenuItemViewSet,
    RestaurantReviewViewSet,
    RestaurantViewSet,
)
from users.views import MeView, RegisterView
from users.browser_auth import CSRFView, BrowserSessionView, BrowserLoginView, BrowserRegisterView, BrowserLogoutView

router = DefaultRouter()
router.register("restaurants", RestaurantViewSet, basename="restaurant")
router.register("categories", MenuCategoryViewSet, basename="category")
router.register("menu-items", MenuItemViewSet, basename="menuitem")
router.register("reviews", RestaurantReviewViewSet, basename="review")
router.register("cart", CartViewSet, basename="cart")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("api/health/", health),
    path("admin/", admin.site.urls),
    # JWT / аутентификация
    path("api/auth/csrf/", CSRFView.as_view(), name="browser_csrf"),
    path("api/auth/session/", BrowserSessionView.as_view(), name="browser_session"),
    path("api/auth/session/login/", BrowserLoginView.as_view(), name="browser_login"),
    path("api/auth/session/register/", BrowserRegisterView.as_view(), name="browser_register"),
    path("api/auth/session/logout/", BrowserLogoutView.as_view(), name="browser_logout"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Ресурсы
    path("api/", include(router.urls)),
    # Документация
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
