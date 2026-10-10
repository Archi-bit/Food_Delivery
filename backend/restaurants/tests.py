from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError
from django.contrib.auth import get_user_model
from .models import Restaurant, MenuCategory, MenuItem, RestaurantReview


class SeedTests(TestCase):
    @override_settings(DEMO_MODE=True)
    def test_seed_preserves_existing_and_is_idempotent(self):
        existing = Restaurant.objects.create(name='Existing', address='Real preserved address', delivery_time=60)
        root = Path(__file__).resolve().parent.parent / '.test-data'
        root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=root) as media, override_settings(MEDIA_ROOT=media):
            call_command('seed_demo', stdout=StringIO())
            counts = (Restaurant.objects.count(), MenuCategory.objects.count(), MenuItem.objects.count(), RestaurantReview.objects.count(), get_user_model().objects.count())
            files = len(list(Path(media).rglob('*.jpg')))
            call_command('seed_demo', stdout=StringIO())
            self.assertEqual(counts, (17, 96, 208, 48, 3))
            self.assertEqual(counts, (Restaurant.objects.count(), MenuCategory.objects.count(), MenuItem.objects.count(), RestaurantReview.objects.count(), get_user_model().objects.count()))
            self.assertEqual(files, len(list(Path(media).rglob('*.jpg'))))
            self.assertFalse(get_user_model().objects.filter(is_staff=True).exists())
            self.assertTrue(all(not user.has_usable_password() for user in get_user_model().objects.all()))
            existing.refresh_from_db()
            self.assertEqual(existing.address, 'Real preserved address')

    @override_settings(DEMO_MODE=False)
    def test_seed_disabled(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Restaurant.objects.count(), 0)


class FoodCategoryFilterTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.pizza = Restaurant.objects.create(name='Пиццерия', address='Демо', delivery_time=25)
        self.lagman = Restaurant.objects.create(name='Лапша', address='Демо', delivery_time=35)
        self.closed = Restaurant.objects.create(name='Закрытая пиццерия', address='Демо', delivery_time=40, is_open=False)
        self.unavailable = Restaurant.objects.create(name='Нет в наличии', address='Демо', delivery_time=40)
        self.dessert = Restaurant.objects.create(name='Кондитерская', address='Демо', delivery_time=30)
        self.add_dish(self.pizza, 'Пицца', 'Маргарита')
        self.add_dish(self.pizza, 'пицца', 'Четыре сыра')
        self.add_dish(self.lagman, 'Основное', 'Домашний лагман')
        self.add_dish(self.lagman, 'Основное', 'Манты с тыквой')
        self.add_dish(self.lagman, 'САЛАТЫ', 'Овощной')
        self.add_dish(self.closed, 'Пицца', 'Маргарита')
        self.add_dish(self.unavailable, 'Пицца', 'Маргарита', available=False)
        self.add_dish(self.dessert, 'Десерты', 'Ягодный чизкейк')
        self.add_dish(self.dessert, 'Десерты', 'Медовый торт')
        for index, stars in enumerate([3, 5]):
            user = get_user_model().objects.create_user(username=f'rating_{index}')
            RestaurantReview.objects.create(restaurant=self.pizza, user=user, stars=stars)

    def add_dish(self, restaurant, category, name, available=True):
        cat, _ = MenuCategory.objects.get_or_create(restaurant=restaurant, name=category)
        return MenuItem.objects.create(category=cat, name=name, price=250, weight=200, is_available=available)

    def test_restaurants_match_available_menu_without_duplicates_or_rating_changes(self):
        response = self.client.get('/api/restaurants/', {'food_category': 'pizza', 'ordering': 'delivery_time'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual([r['id'] for r in response.data['results']], [self.pizza.pk, self.closed.pk])
        self.assertEqual(response.data['results'][0]['avg_rating'], 4.0)
        self.assertEqual(response.data['results'][0]['reviews_count'], 2)

    def test_combines_category_search_and_open_filter(self):
        response = self.client.get('/api/restaurants/', {'food_category': 'pizza', 'is_open': 'true', 'search': 'Пиццерия'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.pizza.pk)
        response = self.client.get('/api/restaurants/', {'food_category': 'lagman', 'search': 'Пиццерия'})
        self.assertEqual(response.data['count'], 0)

    def test_all_food_categories_filter_both_endpoints(self):
        for category, restaurant, count in [('lagman', self.lagman, 1), ('manty', self.lagman, 1), ('salad', self.lagman, 1), ('desserts', self.dessert, 2)]:
            with self.subTest(category=category):
                response = self.client.get('/api/restaurants/', {'food_category': category})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([r['id'] for r in response.data['results']], [restaurant.pk])
                dishes = self.client.get('/api/menu-items/', {'food_category': category, 'is_available': 'true'})
                self.assertEqual(dishes.status_code, 200)
                self.assertEqual(dishes.data['count'], count)

    def test_clear_filter_returns_all_and_invalid_category_is_rejected(self):
        self.assertEqual(self.client.get('/api/restaurants/').data['count'], 5)
        for endpoint in ['restaurants', 'menu-items']:
            response = self.client.get(f'/api/{endpoint}/', {'food_category': 'unknown'})
            self.assertEqual(response.status_code, 400)


class UnicodeRestaurantSearchTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.restaurant = Restaurant.objects.create(
            name='Базилик и тесто', description='Итальянская кухня и ПИЦЦА',
            address='Демо', delivery_time=25,
        )
        category = MenuCategory.objects.create(restaurant=self.restaurant, name='Пицца')
        MenuItem.objects.create(category=category, name='Пицца Маргарита', price=300, weight=250)
        Restaurant.objects.create(name='Лапша', address='Демо', delivery_time=35)

    def test_cyrillic_name_matches_any_case(self):
        for term in ['базилик и тесто', 'Базилик и тесто', 'БАЗИЛИК И ТЕСТО', 'бАзИлИк И тЕсТо', 'зИЛик', '  базилик   тесто  ']:
            with self.subTest(search=term):
                response = self.client.get('/api/restaurants/', {'search': term})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['count'], 1)
                self.assertEqual(response.data['results'][0]['id'], self.restaurant.pk)

    def test_description_and_menu_search_are_case_insensitive(self):
        for endpoint, term in [('restaurants', 'итальянская'), ('restaurants', 'пицца'), ('menu-items', 'пИцЦа мАрГаРиТа'), ('categories', 'пИцЦа')]:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f'/api/{endpoint}/', {'search': term})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['count'], 1)

    def test_search_combines_with_category_open_sort_and_pagination(self):
        response = self.client.get('/api/restaurants/', {
            'search': 'базилик', 'food_category': 'pizza', 'is_open': 'true',
            'ordering': 'delivery_time', 'page': 1,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.restaurant.pk)
        self.assertEqual(self.client.get('/api/restaurants/', {'search': 'базилик лапша'}).data['count'], 0)

    def test_empty_search_and_literal_wildcards(self):
        self.assertEqual(self.client.get('/api/restaurants/', {'search': ''}).data['count'], 2)
        for term in ['%', '_', 'несуществующий']:
            self.assertEqual(self.client.get('/api/restaurants/', {'search': term}).data['count'], 0)

    def test_unicode_case_including_yo_and_latin(self):
        Restaurant.objects.create(name='ТЁПЛЫЙ двор Café', address='Демо', delivery_time=30)
        response = self.client.get('/api/restaurants/', {'search': 'тёплый CAFÉ'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
