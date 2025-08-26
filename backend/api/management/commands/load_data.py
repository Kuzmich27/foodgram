# foodgram/management/commands/load_data.py
import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Recipe, Tag, Ingredient
from django.utils import timezone

CustomUser = get_user_model()

class Command(BaseCommand):
    help = 'Load all data from JSON files'

    def handle(self, *args, **options):
        base_path = 'data/'
        
        # 1. Загрузка пользователей
        self.stdout.write('👥 Загрузка пользователей...')
        users_path = os.path.join(base_path, 'users.json')
        if os.path.exists(users_path):
            with open(users_path, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            for user_data in users_data:
                if user_data['model'] == 'users.customuser':
                    self.load_user(user_data)
        
        # 2. Загрузка тегов
        self.stdout.write('🏷️ Загрузка тегов...')
        tags_path = os.path.join(base_path, 'tags.json')
        if os.path.exists(tags_path):
            with open(tags_path, 'r', encoding='utf-8') as f:
                tags_data = json.load(f)
            
            for tag_data in tags_data:
                if tag_data['model'] == 'recipes.tag':
                    self.load_tag(tag_data)
        
        # 3. Загрузка ингредиентов
        self.stdout.write('🥬 Загрузка ингредиентов...')
        ingredients_path = os.path.join(base_path, 'ingredients.json')
        if os.path.exists(ingredients_path):
            with open(ingredients_path, 'r', encoding='utf-8') as f:
                ingredients_data = json.load(f)
            
            for ingredient_data in ingredients_data:
                if ingredient_data['model'] == 'recipes.ingredient':
                    self.load_ingredient(ingredient_data)
        
        # 4. Загрузка рецептов (последними, после пользователей!)
        self.stdout.write('🍳 Загрузка рецептов...')
        recipes_path = os.path.join(base_path, 'recipes.json')
        if os.path.exists(recipes_path):
            with open(recipes_path, 'r', encoding='utf-8') as f:
                recipes_data = json.load(f)
            
            for recipe_data in recipes_data:
                if recipe_data['model'] == 'recipes.recipe':
                    self.load_recipe(recipe_data)
        
        self.stdout.write(self.style.SUCCESS('✅ Все данные успешно загружены!'))

    def load_user(self, user_data):
        fields = user_data['fields']
        user, created = CustomUser.objects.get_or_create(
            id=user_data['pk'],
            defaults={
                'username': fields['username'],
                'email': fields['email'],
                'is_superuser': fields.get('is_superuser', False),
                'is_staff': fields.get('is_staff', False),
                'is_active': fields.get('is_active', True),
                'first_name': fields.get('first_name', ''),
                'last_name': fields.get('last_name', ''),
                'date_joined': fields.get('date_joined', timezone.now())
            }
        )
        if created:
            user.set_password(fields['password'])
            user.save()

    def load_tag(self, tag_data):
        fields = tag_data['fields']
        Tag.objects.get_or_create(
            id=tag_data['pk'],
            defaults={
                'name': fields['name'],
                'color': fields.get('color', ''),
                'slug': fields.get('slug', '')
            }
        )

    def load_ingredient(self, ingredient_data):
        fields = ingredient_data['fields']
        Ingredient.objects.get_or_create(
            id=ingredient_data['pk'],
            defaults={
                'name': fields['name'],
                'measurement_unit': fields.get('measurement_unit', '')
            }
        )

    def load_recipe(self, recipe_data):
        fields = recipe_data['fields']
        try:
            recipe, created = Recipe.objects.get_or_create(
                id=recipe_data['pk'],
                defaults={
                    'author_id': fields['author'],
                    'name': fields['name'],
                    'image': fields.get('image', ''),
                    'text': fields.get('text', ''),
                    'cooking_time': fields.get('cooking_time', 0)
                }
            )
            if created and 'tags' in fields:
                recipe.tags.set(fields['tags'])
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                f'⚠️ Пользователь {fields["author"]} не найден для рецепта {recipe_data["pk"]}'
            ))