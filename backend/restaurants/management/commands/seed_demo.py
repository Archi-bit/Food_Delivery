"""Идемпотентные вымышленные данные и собственные локальные иллюстрации."""
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from restaurants.models import Restaurant, MenuCategory, MenuItem, RestaurantReview

NAMES = ['Тёплый двор', 'Базилик и тесто', 'Рисовый сад', 'Кочевник kitchen', 'Зелёная миска', 'Печь на Чуй', 'Мята café', 'Лапша и пар', 'Бургерная 312', 'Пловный дом', 'Сыр и корочка', 'Утренний стол', 'Манты у гор', 'Оранжевый вок', 'Сладкая пауза', 'Суповая ложка']
MENUS = [('Основное', [('Плов с говядиной', 340, 350), ('Манты с тыквой', 290, 300), ('Лагман домашний', 320, 380)]), ('Пицца', [('Пицца с томатами', 490, 450), ('Пицца четыре сыра', 590, 430)]), ('Салаты', [('Салат с овощами', 230, 220), ('Салат с курицей', 290, 250)]), ('Завтраки', [('Сырники со сметаной', 260, 200), ('Омлет с зеленью', 210, 180)]), ('Десерты', [('Медовый торт', 240, 150), ('Ягодный чизкейк', 280, 160)]), ('Напитки', [('Домашний морс', 120, 300), ('Мятный лимонад', 140, 300)])]

from restaurants.management.demo_art import artwork

class Command(BaseCommand):
    help = 'Создать 16 вымышленных ресторанов; только при DEMO_MODE=1, без администратора.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError('Требуется DEMO_MODE=1')
        User = get_user_model()
        reviewers=[]
        for i in range(3):
            user, created = User.objects.get_or_create(username=f'portfolio_reviewer_{i}', defaults={'first_name': ['Айжан', 'Тимур', 'Алина'][i], 'email': f'reviewer{i}@example.invalid'})
            if created: user.set_unusable_password(); user.save()
            reviewers.append(user)
        for index, name in enumerate(NAMES):
            rest, created = Restaurant.objects.get_or_create(name=name, defaults={'address': f'Демо-адрес: Бишкек, ул. Учебная, {index+1}', 'description': f'{name} — вымышленная кухня Бишкека. Свежие ингредиенты, домашние рецепты и обеды для хорошего дня. Демонстрационный ресторан.', 'delivery_time': 20 + index % 6 * 5, 'min_order_price': 300, 'is_open': index != 15})
            if rest.description.startswith(f'{name} — вымышленная') and 'Демо-контакт:' not in rest.description:
                rest.description += f' Демо-контакт: kitchen{index}@example.invalid (не работает).'
                rest.save(update_fields=['description'])
            if created or not rest.logo or 'demo-restaurant-' in rest.logo.name and 'v2-' not in rest.logo.name:
                rest.logo.save(f'demo-restaurant-v2-{index}.jpg', ContentFile(artwork(index, MENUS[index % len(MENUS)][0])))
            for ci, (category, dishes) in enumerate(MENUS):
                cat, _ = MenuCategory.objects.get_or_create(restaurant=rest, name=category)
                for di, (dish, price, weight) in enumerate(dishes):
                    item, fresh = MenuItem.objects.get_or_create(category=cat, name=dish, defaults={'price': price+index*5, 'weight': weight, 'description': f'{dish}: приготовлено по домашнему рецепту из свежих ингредиентов.', 'is_available': not (ci == 4 and di == 1 and index % 3 == 0)})
                    if fresh or not item.photo or 'demo-dish-' in item.photo.name and 'v2-' not in item.photo.name:
                        item.photo.save(f'demo-dish-v2-{index}-{ci}-{di}.jpg', ContentFile(artwork(index+ci+di, category)))
            for ri, user in enumerate(reviewers):
                RestaurantReview.objects.get_or_create(restaurant=rest, user=user, defaults={'stars': 4+(index+ri)%2, 'comment': 'Демонстрационный отзыв: вкусный обед, аккуратная упаковка.'})
        self.stdout.write(self.style.SUCCESS('16 ресторанов, 208 блюд, 48 отзывов. Реальных заведений и администраторов не создано.'))
