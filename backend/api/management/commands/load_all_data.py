# management/commands/load_all_data.py
import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from recipes.models import Recipe, Tag, Ingredient
from django.utils import timezone

CustomUser = get_user_model()

class Command(BaseCommand):
    help = 'Load all data from JSON files'

    def handle(self, *args, **options):
        # Загрузка пользователей
        with open('data/users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        for user_data in users_data:
            if user_data['model'] == 'users.CustomUser':
                self.load_user(user_data)

        # Загрузка рецептов
        with open('data/recipes.json', 'r', encoding='utf-8') as f:
            recipes_data = json.load(f)
        
        for recipe_data in recipes_data:
            if recipe_data['model'] == 'recipes.recipe':
                self.load_recipe(recipe_data)

    def load_user(self, user_data):
        fields = user_data['fields']
        user = CustomUser(
            id=user_data['pk'],
            username=fields['username'],
            email=fields['email'],
            is_superuser=fields.get('is_superuser', False),
            is_staff=fields.get('is_staff', False),
            is_active=fields.get('is_active', True),
            first_name=fields.get('first_name', ''),
            last_name=fields.get('last_name', ''),
            date_joined=fields.get('date_joined', timezone.now())
        )
        user.set_password(fields['password'])
        user.save()

    def load_recipe(self, recipe_data):
        fields = recipe_data['fields']
        recipe = Recipe(
            id=recipe_data['pk'],
            author_id=fields['author'],  # ORM автоматически разрешит внешний ключ
            name=fields['name'],
            image=fields.get('image', ''),
            text=fields.get('text', ''),
            pub_date=fields.get('pub_date', timezone.now()),
            cooking_time=fields.get('cooking_time', 0)
        )
        recipe.save()