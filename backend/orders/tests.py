from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Cart, Order
from restaurants.models import MenuCategory, MenuItem, Restaurant, RestaurantReview

User = get_user_model()


class BaseCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", "u@x.com", "pass12345!", delivery_address="Бишкек, 1")
        self.other = User.objects.create_user("other", "o@x.com", "pass12345!")
        self.admin = User.objects.create_user("admin", "a@x.com", "pass12345!", is_staff=True)
        self.r1 = Restaurant.objects.create(name="Pizza", address="a", delivery_time=30, min_order_price=500)
        self.r2 = Restaurant.objects.create(name="Sushi", address="b", delivery_time=40, min_order_price=0, is_open=False)
        self.c1 = MenuCategory.objects.create(name="Pizzas", restaurant=self.r1)
        self.c2 = MenuCategory.objects.create(name="Rolls", restaurant=self.r2)
        self.pizza = MenuItem.objects.create(name="Margherita", price="450.00", weight=400, category=self.c1)
        self.cola = MenuItem.objects.create(name="Cola", price="100.00", weight=330, category=self.c1)
        self.gone = MenuItem.objects.create(name="Gone", price="50.00", weight=100, category=self.c1, is_available=False)
        self.roll = MenuItem.objects.create(name="Roll", price="300.00", weight=200, category=self.c2)


class AuthTests(BaseCase):
    def test_register_and_me(self):
        r = self.client.post("/api/auth/register/", {
            "username": "new", "email": "n@x.com", "password": "StrongPass123!", "password2": "StrongPass123!",
            "phone_number": "+996555123456",
        })
        self.assertEqual(r.status_code, 201, r.data)
        access = r.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.data["username"], "new")
        self.assertEqual(self.client.patch("/api/auth/me/", {"delivery_address": "X"}).data["delivery_address"], "X")

    def test_register_password_mismatch(self):
        r = self.client.post("/api/auth/register/", {
            "username": "n", "email": "n@x.com", "password": "StrongPass123!", "password2": "other"})
        self.assertEqual(r.status_code, 400)

    def test_jwt_obtain(self):
        r = self.client.post("/api/auth/token/", {"username": "user", "password": "pass12345!"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)


class PermissionTests(BaseCase):
    def test_anon_can_read_but_not_write(self):
        self.assertEqual(self.client.get("/api/restaurants/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/restaurants/{self.r1.id}/").status_code, 200)
        self.assertEqual(self.client.get("/api/menu-items/").status_code, 200)
        self.assertEqual(self.client.post("/api/restaurants/", {}).status_code, 401)

    def test_regular_user_cannot_manage_menu(self):
        self.client.force_authenticate(self.user)
        r = self.client.post("/api/menu-items/", {"name": "x", "price": "1", "weight": 1, "category": self.c1.id})
        self.assertEqual(r.status_code, 403)

    def test_staff_can_manage_menu(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post("/api/menu-items/", {"name": "x", "price": "10", "weight": 5, "category": self.c1.id})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.delete(f"/api/menu-items/{r.data['id']}/").status_code, 204)

    def test_cart_requires_auth(self):
        self.assertEqual(self.client.get("/api/cart/").status_code, 401)


class RestaurantQueryTests(BaseCase):
    def test_filter_search_ordering(self):
        r = self.client.get("/api/restaurants/?is_open=true")
        self.assertEqual([x["name"] for x in r.data["results"]], ["Pizza"])
        r = self.client.get("/api/restaurants/?search=sush")
        self.assertEqual(len(r.data["results"]), 1)
        RestaurantReview.objects.create(restaurant=self.r1, user=self.user, stars=3)
        RestaurantReview.objects.create(restaurant=self.r2, user=self.user, stars=5)
        r = self.client.get("/api/restaurants/?ordering=-avg_rating")
        self.assertEqual([x["name"] for x in r.data["results"]], ["Sushi", "Pizza"])
        self.assertEqual(r.data["results"][0]["avg_rating"], 5.0)

    def test_menu_filters_and_price_ordering(self):
        r = self.client.get(f"/api/menu-items/?category={self.c1.id}&is_available=true&ordering=price")
        self.assertEqual([x["name"] for x in r.data["results"]], ["Cola", "Margherita"])
        r = self.client.get(f"/api/menu-items/?category={self.c1.id}&ordering=-price")
        self.assertEqual(r.data["results"][0]["name"], "Margherita")

    def test_detail_nested(self):
        r = self.client.get(f"/api/restaurants/{self.r1.id}/")
        self.assertEqual(r.data["categories"][0]["items"][0]["name"], "Cola")

    def test_avg_rating_method(self):
        self.assertEqual(self.r1.get_avg_rating(), 0.0)
        RestaurantReview.objects.create(restaurant=self.r1, user=self.user, stars=4)
        RestaurantReview.objects.create(restaurant=self.r1, user=self.other, stars=5)
        self.assertEqual(self.r1.get_avg_rating(), 4.5)


class ReviewTests(BaseCase):
    def test_stars_validation_and_uniqueness(self):
        self.client.force_authenticate(self.user)
        for bad in (0, 6):
            r = self.client.post("/api/reviews/", {"restaurant": self.r1.id, "stars": bad})
            self.assertEqual(r.status_code, 400)
        ok = self.client.post("/api/reviews/", {"restaurant": self.r1.id, "stars": 5, "comment": "ok"})
        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(ok.data["user"], "user")
        dup = self.client.post("/api/reviews/", {"restaurant": self.r1.id, "stars": 4})
        self.assertEqual(dup.status_code, 400)

    def test_cannot_edit_foreign_review(self):
        rv = RestaurantReview.objects.create(restaurant=self.r1, user=self.other, stars=2)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.patch(f"/api/reviews/{rv.id}/", {"stars": 5}).status_code, 403)

    def test_anon_cannot_review(self):
        self.assertEqual(self.client.post("/api/reviews/", {"restaurant": self.r1.id, "stars": 5}).status_code, 401)


class CartTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_add_update_delete_clear(self):
        r = self.client.post("/api/cart/items/", {"item": self.pizza.id, "quantity": 2})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["total_price"], "900.00")
        r = self.client.post("/api/cart/items/", {"item": self.pizza.id, "quantity": 1})
        self.assertEqual(r.data["items"][0]["quantity"], 3)
        cid = r.data["items"][0]["id"]
        r = self.client.patch(f"/api/cart/items/{cid}/", {"quantity": 1})
        self.assertEqual(r.data["total_price"], "450.00")
        r = self.client.delete(f"/api/cart/items/{cid}/")
        self.assertEqual(r.data["items"], [])
        self.client.post("/api/cart/items/", {"item": self.cola.id})
        r = self.client.post("/api/cart/clear/")
        self.assertEqual(r.data["items"], [])

    def test_unavailable_item_rejected(self):
        r = self.client.post("/api/cart/items/", {"item": self.gone.id})
        self.assertEqual(r.status_code, 400)

    def test_other_restaurant_rejected(self):
        self.client.post("/api/cart/items/", {"item": self.pizza.id})
        r = self.client.post("/api/cart/items/", {"item": self.roll.id})
        self.assertEqual(r.status_code, 400)

    def test_cannot_touch_foreign_cart_item(self):
        self.client.force_authenticate(self.other)
        ci = self.client.post("/api/cart/items/", {"item": self.pizza.id}).data["items"][0]["id"]
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(f"/api/cart/items/{ci}/").status_code, 404)
        self.assertEqual(self.client.get("/api/cart/").data["items"], [])


class OrderTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_checkout_success_fixes_price_and_clears_cart(self):
        self.client.post("/api/cart/items/", {"item": self.pizza.id, "quantity": 1})
        self.client.post("/api/cart/items/", {"item": self.cola.id, "quantity": 1})
        r = self.client.post("/api/orders/checkout/", {})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["total_price"], "550.00")
        self.assertEqual(r.data["status"], "new")
        self.assertEqual(r.data["delivery_address"], "Бишкек, 1")
        self.assertEqual(Cart.objects.get(user=self.user).items.count(), 0)
        # цена зафиксирована
        self.pizza.price = Decimal("999.00"); self.pizza.save()
        order = Order.objects.get(pk=r.data["id"])
        self.assertEqual(order.get_total_price(), Decimal("550.00"))
        self.assertEqual(order.items.count(), 2)

    def test_checkout_below_minimum(self):
        self.client.post("/api/cart/items/", {"item": self.cola.id})
        r = self.client.post("/api/orders/checkout/", {"delivery_address": "x"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Cart.objects.get(user=self.user).items.count(), 1)

    def test_checkout_empty_cart(self):
        self.assertEqual(self.client.post("/api/orders/checkout/", {}).status_code, 400)

    def test_checkout_item_became_unavailable(self):
        self.client.post("/api/cart/items/", {"item": self.pizza.id, "quantity": 2})
        self.pizza.is_available = False; self.pizza.save()
        self.assertEqual(self.client.post("/api/orders/checkout/", {}).status_code, 400)

    def test_checkout_closed_restaurant(self):
        self.client.post("/api/cart/items/", {"item": self.roll.id})
        self.assertEqual(self.client.post("/api/orders/checkout/", {}).status_code, 400)

    def test_checkout_requires_address(self):
        self.user.delivery_address = ""; self.user.save()
        self.client.post("/api/cart/items/", {"item": self.pizza.id, "quantity": 2})
        self.assertEqual(self.client.post("/api/orders/checkout/", {}).status_code, 400)

    def _make_order(self):
        self.client.post("/api/cart/items/", {"item": self.pizza.id, "quantity": 2})
        return self.client.post("/api/orders/checkout/", {}).data["id"]

    def test_user_sees_only_own_orders(self):
        oid = self._make_order()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/orders/").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/orders/{oid}/").status_code, 404)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/orders/").data["count"], 1)

    def test_status_change_staff_only_and_forward_only(self):
        oid = self._make_order()
        self.assertEqual(self.client.patch(f"/api/orders/{oid}/status/", {"status": "preparing"}).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f"/api/orders/{oid}/status/", {"status": "preparing"}).status_code, 200)
        self.assertEqual(self.client.patch(f"/api/orders/{oid}/status/", {"status": "new"}).status_code, 400)
        self.assertEqual(self.client.patch(f"/api/orders/{oid}/status/", {"status": "bogus"}).status_code, 400)
        r = self.client.patch(f"/api/orders/{oid}/status/", {"status": "delivered"})
        self.assertEqual(r.data["status"], "delivered")

    def test_user_cannot_delete_or_edit_order(self):
        oid = self._make_order()
        self.assertEqual(self.client.delete(f"/api/orders/{oid}/").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/orders/{oid}/", {"status": "delivered"}).status_code, 405)


class SchemaTests(BaseCase):
    def test_schema_and_swagger(self):
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        self.assertEqual(self.client.get("/api/schema/swagger-ui/").status_code, 200)


from django.test import override_settings
from orders.models import DemoPayment

@override_settings(DEMO_MODE=True)
class DemoTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def _make_order(self):
        self.client.post("/api/cart/items/", {"item": self.pizza.id, "quantity": 2})
        return self.client.post("/api/orders/checkout/", {}).data["id"]

    def test_demo_payment_and_delivery(self):
        oid = self._make_order()
        self.assertEqual(self.client.post(f'/api/orders/{oid}/demo-advance/').status_code, 400)
        self.assertFalse(self.client.post(f'/api/orders/{oid}/demo-payment/', {'success': False}).data['success'])
        self.assertTrue(self.client.post(f'/api/orders/{oid}/demo-payment/', {'success': True}).data['success'])
        # A successful demo payment is idempotent and cannot be reversed by a retry.
        self.assertTrue(self.client.post(f'/api/orders/{oid}/demo-payment/', {'success': False}).data['success'])
        for expected in ('preparing', 'on_way', 'delivered', 'delivered'):
            self.assertEqual(self.client.post(f'/api/orders/{oid}/demo-advance/').data['status'], expected)
        self.assertEqual(DemoPayment.objects.count(), 1)

    def test_demo_foreign_order(self):
        oid = self._make_order()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(f'/api/orders/{oid}/demo-payment/', {'success': True}).status_code, 404)
        self.assertEqual(self.client.post(f'/api/orders/{oid}/demo-advance/').status_code, 404)

    @override_settings(DEMO_MODE=False)
    def test_demo_disabled(self):
        oid = self._make_order()
        self.assertEqual(self.client.post(f'/api/orders/{oid}/demo-payment/', {'success': True}).status_code, 404)
        self.assertEqual(self.client.post(f'/api/orders/{oid}/demo-advance/').status_code, 404)


class ExtraValidationTests(BaseCase):
    def test_token_refresh(self):
        tokens = self.client.post('/api/auth/token/', {'username': 'user', 'password': 'pass12345!'}).data
        self.assertEqual(self.client.post('/api/auth/token/refresh/', {'refresh': tokens['refresh']}).status_code, 200)
        self.assertEqual(self.client.post('/api/auth/token/refresh/', {'refresh': 'invalid'}).status_code, 401)

    def test_profile_cannot_escalate_privileges(self):
        self.client.force_authenticate(self.user)
        self.client.patch('/api/auth/me/', {'is_staff': True, 'username': 'admin'})
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertEqual(self.user.username, 'user')

    def test_quantity_limit_and_rollback(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/cart/items/', {'item': self.pizza.id, 'quantity': 99}).status_code, 201)
        self.assertEqual(self.client.post('/api/cart/items/', {'item': self.pizza.id}).status_code, 400)
        self.assertEqual(self.client.get('/api/cart/').data['items'][0]['quantity'], 99)

    def test_complete_jwt_workflow(self):
        result = self.client.post('/api/auth/register/', {'username': 'journey', 'email': 'journey@example.invalid', 'password': 'JourneySecure237!', 'password2': 'JourneySecure237!'})
        self.assertEqual(result.status_code, 201)
        login = self.client.post('/api/auth/token/', {'username': 'journey', 'password': 'JourneySecure237!'})
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['access'])
        restaurant = self.client.get(f'/api/restaurants/{self.r1.id}/')
        self.assertIn('categories', restaurant.data)
        self.assertEqual(self.client.post('/api/cart/items/', {'item': self.pizza.id, 'quantity': 2}).status_code, 201)
        self.assertEqual(self.client.patch('/api/auth/me/', {'phone_number': '+996555123456', 'delivery_address': 'Бишкек, учебный адрес 12'}).status_code, 200)
        order = self.client.post('/api/orders/checkout/', {})
        self.assertEqual(order.status_code, 201)
        self.assertEqual(self.client.get('/api/orders/').data['results'][0]['id'], order.data['id'])
        self.assertEqual(self.client.get('/api/cart/').data['items'], [])


from django.test import TransactionTestCase
from django.db import connection, connections
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from orders.models import CartItem
from rest_framework.test import APIClient

@skipUnless(connection.vendor == 'postgresql', 'Row-lock concurrency requires PostgreSQL')
class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user('concurrent', password='ParallelSecure23!', delivery_address='Бишкек, учебная 1')
        self.restaurant = Restaurant.objects.create(name='Parallel', address='Demo', delivery_time=20)
        category = MenuCategory.objects.create(name='Menu', restaurant=self.restaurant)
        self.item = MenuItem.objects.create(name='Lunch', category=category, price='350.00', weight=250)
        self.cart = Cart.objects.create(user=self.user)

    def parallel(self, url, payload):
        barrier = Barrier(2)
        def send(_):
            client = APIClient()
            client.force_authenticate(self.user)
            try:
                barrier.wait(timeout=10)
                return client.post(url, payload).status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(send, range(2)))

    def test_parallel_add_preserves_quantity(self):
        self.assertEqual(self.parallel('/api/cart/items/', {'item': self.item.id}), [201, 201])
        self.assertEqual(self.cart.items.get().quantity, 2)

    def test_parallel_checkout_creates_one_order(self):
        CartItem.objects.create(cart=self.cart, item=self.item, quantity=2)
        self.assertEqual(sorted(self.parallel('/api/orders/checkout/', {})), [201, 400])
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.cart.items.count(), 0)


class UploadTests(BaseCase):
    def test_avatar_rejects_unsupported_format(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        content = BytesIO()
        Image.new('RGB', (10, 10)).save(content, 'GIF')
        self.client.force_authenticate(self.user)
        response = self.client.patch('/api/auth/me/', {'avatar': SimpleUploadedFile('avatar.gif', content.getvalue(), content_type='image/gif')}, format='multipart')
        self.assertEqual(response.status_code, 400)
