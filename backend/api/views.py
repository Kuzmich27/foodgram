import logging
logger = logging.getLogger(__name__)

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, F
from collections import defaultdict

from api.models import Recipe, Tag, Ingredient, Follow, Favorite, ShoppingCart, IngredientInRecipe
from api.serializers import (
    RecipeReadSerializer,
    RecipeWriteSerializer,
    TagSerializer,
    IngredientSerializer,
    FollowSerializer,
    CustomUserSerializer,
    AvatarSerializer,
    SubscriptionSerializer
)
from users.models import CustomUser

from api.permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from api.pagination import RecipePagination, SubscriptionPagination
from api.filter import RecipeFilter


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    pagination_class = RecipePagination
    filterset_class = RecipeFilter

    def get_queryset(self):
        queryset = Recipe.objects.all().prefetch_related(
            'tags', 'ingredient_in_recipe__ingredient'
        ).select_related('author')

        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        if self.request.query_params.get('is_favorited') == '1' and self.request.user.is_authenticated:
            queryset = queryset.filter(favorites__user=self.request.user)

        if self.request.query_params.get('is_in_shopping_cart') == '1' and self.request.user.is_authenticated:
            queryset = queryset.filter(in_shopping_cart__user=self.request.user)

        return queryset.order_by('-pub_date')

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

    def perform_create(self, serializer):
        logger.debug(f"PERFORM_CREATE - Saving recipe for user: {self.request.user}")
        serializer.save()

    def create(self, request, *args, **kwargs):
        logger.debug(f"CREATE VIEW - Request data: {request.data}")

        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()

        read_serializer = RecipeReadSerializer(instance, context={'request': request})

        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post', 'delete'], url_path='favorite')
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            Favorite.objects.get_or_create(user=request.user, recipe=recipe)
            return Response({'status': 'added to favorites'}, status=status.HTTP_201_CREATED)
        Favorite.objects.filter(user=request.user, recipe=recipe).delete()
        return Response({'status': 'removed from favorites'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            ShoppingCart.objects.get_or_create(user=request.user, recipe=recipe)
            return Response({'status': 'added to shopping cart'}, status=status.HTTP_201_CREATED)
        ShoppingCart.objects.filter(user=request.user, recipe=recipe).delete()
        return Response({'status': 'removed from shopping cart'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        """Скачать список покупок в формате TXT с красивым форматированием"""
        shopping_cart_recipes = ShoppingCart.objects.filter(
            user=request.user
        ).values_list('recipe', flat=True)

        ingredients = IngredientInRecipe.objects.filter(
            recipe__in=shopping_cart_recipes
        ).values(
            'ingredient__name',
            'ingredient__unit_of_measurement'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        lines = []
        lines.append("СПИСОК ПОКУПОК")
        lines.append("")
        lines.append("Ингредиенты:")
        lines.append("-" * 40)

        for i, ingredient in enumerate(ingredients, 1):
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__unit_of_measurement']
            amount = ingredient['total_amount']
            lines.append(f"{i:2d}. {name} ({unit}) — {amount}")

        lines.append("-" * 40)
        lines.append(f"Всего: {len(ingredients)} ингредиентов")

        text_content = "\n".join(lines)

        response = HttpResponse(text_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'

        return response

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        try:
            image_url = request.build_absolute_uri(recipe.image.url) if recipe.image else None
        except:
            image_url = None

        return Response({
            'url': image_url
        }, status=status.HTTP_200_OK)


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['get', 'post', 'put', 'patch', 'delete'],
        url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated]
    )
    def set_avatar(self, request):
        user = request.user

        if request.method == 'GET':
            serializer = AvatarSerializer(user, context={'request': request})
            return Response(serializer.data)

        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = None
            user.save()
            return Response(
                {'status': 'Avatar deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )

        else:
            if 'avatar' not in request.data:
                return Response(
                    {'error': 'Avatar field is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            avatar_data = request.data['avatar']
            logger.debug(f"Avatar data type: {type(avatar_data)}")
            if isinstance(avatar_data, str):
                logger.debug(f"Avatar data starts with: {avatar_data[:100]}")

            serializer = AvatarSerializer(
                user,
                data=request.data,
                context={'request': request},
                partial=True
            )

            if serializer.is_valid():
                serializer.save()
                return_serializer = AvatarSerializer(user, context={'request': request})
                return Response(return_serializer.data, status=status.HTTP_200_OK)

            logger.error("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        permission_classes=[permissions.IsAuthenticated],
        pagination_class=SubscriptionPagination
    )
    def subscriptions(self, request):
        user = request.user
        follows = Follow.objects.filter(user=user)
        authors = [follow.author for follow in follows]

        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            authors,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe')
    def subscribe(self, request, pk=None):
        """Умный метод подписки/отписки"""
        author = get_object_or_404(CustomUser, pk=pk)

        if request.user == author:
            return Response(
                {'error': 'Cannot subscribe to yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем существующую подписку
        follow_exists = Follow.objects.filter(user=request.user, author=author).exists()

        if request.method == 'POST':
            if follow_exists:
                # Если уже подписан - возвращаем успех вместо ошибки
                return Response(
                    {'status': 'already subscribed', 'message': 'Already subscribed to this user'},
                    status=status.HTTP_200_OK
                )

            # Создаем подписку
            follow = Follow.objects.create(user=request.user, author=author)
            return Response(
                {'status': 'subscribed', 'follow_id': follow.id},
                status=status.HTTP_201_CREATED
            )
        
        else:  # DELETE
            if not follow_exists:
                # Если не подписан - возвращаем ошибку
                return Response(
                    {'error': 'Not subscribed to this user'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Удаляем подписку
            follow = get_object_or_404(Follow, user=request.user, author=author)
            follow.delete()
            return Response({'status': 'unsubscribed'}, status=status.HTTP_200_OK)
        

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]


class FollowViewSet(viewsets.ModelViewSet):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
