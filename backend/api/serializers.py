from rest_framework import serializers
from django.core.files.base import ContentFile
import base64
import logging

from api.models import Recipe, Tag, Ingredient, IngredientInRecipe, Follow, Favorite, ShoppingCart
from users.models import CustomUser

logger = logging.getLogger(__name__)


class Base64ImageField(serializers.ImageField):
    """Поле для кодирования/декодирования изображений в Base64."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    measurement_unit = serializers.CharField(source='unit_of_measurement')

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = ('id',)


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.unit_of_measurement')

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'first_name', 'last_name', 'email')


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = AuthorSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        read_only=True,
        source='ingredient_in_recipe'  # ✅ Правильный source
    )
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (
            request and request.user.is_authenticated and
            Favorite.objects.filter(user=request.user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (
            request and request.user.is_authenticated and
            ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()
        )


class IngredientWriteSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1)

    def create(self, validated_data):
        # Не используется напрямую
        pass

    def update(self, instance, validated_data):
        # Не используется напрямую
        pass


class RecipeWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = IngredientWriteSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def to_internal_value(self, data):
        # Удаляем author из входящих данных, если он есть
        if hasattr(data, 'copy'):
            data = data.copy()
            if 'author' in data:
                del data['author']
        return super().to_internal_value(data)

    def create(self, validated_data):
        logger.debug(f"CREATE - Validated data keys: {list(validated_data.keys())}")

        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        # Валидация cooking_time
        cooking_time = validated_data.get('cooking_time')
        if cooking_time < 1:
            raise serializers.ValidationError({
                'cooking_time': 'Время приготовления должно быть больше 0'
            })

        # Явно удаляем author из validated_data
        if 'author' in validated_data:
            del validated_data['author']
        logger.debug(f"CREATE - Validated data after author removal: {list(validated_data.keys())}")

        # Создаем рецепт поэтапно - сначала базовый объект, потом сохраняем
        recipe = Recipe(
            author=self.context['request'].user,
            **validated_data
        )
        recipe.save()  # ✅ Сохраняем сначала без ManyToMany полей

        # Устанавливаем теги (ManyToMany поле)
        recipe.tags.set(tags_data)

        # Создаем связи с ингредиентами
        for ingredient_data in ingredients_data:
            if ingredient_data['amount'] < 1:
                raise serializers.ValidationError({
                    'ingredients': 'Количество ингредиента должно быть больше 0'
                })

            IngredientInRecipe.objects.create(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )

        logger.debug(f"CREATE - Recipe created: {recipe.id}")
        return recipe

    def update(self, instance, validated_data):
        logger.debug(f"UPDATE - Validated data: {validated_data}")

        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        # Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            # Удаляем старые ингредиенты и добавляем новые
            instance.ingredient_in_recipe.all().delete()
            for ingredient_data in ingredients_data:
                IngredientInRecipe.objects.create(
                    recipe=instance,
                    ingredient=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )

        instance.save()
        logger.debug(f"UPDATE - Recipe updated: {instance.id}")
        return instance


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ('user', 'author')
        read_only_fields = ('user',)  # Только user должен быть read_only
    
    def validate(self, data):
        # Проверка, что пользователь не подписывается на себя
        if self.context['request'].user == data['author']:
            raise serializers.ValidationError("Нельзя подписаться на самого себя")
        
        # Проверка на дубликат подписки
        if Follow.objects.filter(user=self.context['request'].user, author=data['author']).exists():
            raise serializers.ValidationError("Вы уже подписаны на этого пользователя")
        
        return data

class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        read_only_fields = ('user',)


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        read_only_fields = ('user',)


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 'avatar'
        )


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = CustomUser
        fields = ['avatar']

    def to_representation(self, instance):
        request = self.context.get('request')
        if instance.avatar and request:
            return {"avatar": request.build_absolute_uri(instance.avatar.url)}
        return {"avatar": None}

    def update(self, instance, validated_data):
        avatar = validated_data.get('avatar')

        if avatar is not None:
            if instance.avatar:
                instance.avatar.delete(save=False)
            instance.avatar = avatar
        elif 'avatar' in validated_data and validated_data['avatar'] is None:
            if instance.avatar:
                instance.avatar.delete(save=False)
            instance.avatar = None

        instance.save()
        return instance


class SubscriptionSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name', 
            'avatar', 'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', 3) if request else 3

        try:
            recipes_limit = int(recipes_limit)
        except (ValueError, TypeError):
            recipes_limit = 3

        recipes = obj.recipes.all()[:recipes_limit]
        return RecipeShortSerializer(recipes, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')