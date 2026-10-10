"""Start isolated browser-test backend without touching the user's database."""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'backend'))
os.environ.update(DJANGO_SETTINGS_MODULE='config.settings', DJANGO_DEBUG='1', DEMO_MODE='1')
# Keep all test data inside this project, separate from existing SQLite/media.
os.environ['SQLITE_PATH'] = str(root / 'backend' / '.test-data' / 'e2e.sqlite3')
os.environ['MEDIA_ROOT'] = str(root / 'backend' / '.test-data' / 'media')
(root / 'backend' / '.test-data').mkdir(exist_ok=True)
import django
from django.core.management import call_command

django.setup()
call_command('migrate', verbosity=0)
call_command('seed_demo', verbosity=0)
# Distinct menus prove category filtering against the real API. Test DB only.
from restaurants.models import Restaurant, MenuCategory, MenuItem
for food, category, dish in [('пицца', 'Пицца', 'Маргарита'), ('лагман', 'Основное', 'Домашний лагман')]:
    restaurant, _ = Restaurant.objects.get_or_create(
        name=f'E2E кухня: {food}', defaults={'address': 'Изолированные тестовые данные', 'delivery_time': 60},
    )
    menu, _ = MenuCategory.objects.get_or_create(restaurant=restaurant, name=category)
    MenuItem.objects.get_or_create(category=menu, name=dish, defaults={'price': 300, 'weight': 250})
call_command('runserver', '127.0.0.1:18080', use_reloader=False)
