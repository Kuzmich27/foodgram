import logging
logger = logging.getLogger(__name__)

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

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
        # Уберите передачу author, так как он уже устанавливается в сериализаторе
        serializer.save()

    def create(self, request, *args, **kwargs):
        logger.debug(f"CREATE VIEW - Request data: {request.data}")

        # Используем WriteSerializer для создания
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()

        # Используем ReadSerializer для ответа
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
        return Response({'status': 'download shopping cart'}, status=status.HTTP_200_OK)


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

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
        author = get_object_or_404(CustomUser, pk=pk)

        if request.method == 'POST':
            if request.user == author:
                return Response(
                    {'error': 'Cannot subscribe to yourself'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверяем существующую подписку
            if Follow.objects.filter(user=request.user, author=author).exists():
                return Response(
                    {'error': 'Already subscribed to this user'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Создаем подписку напрямую, без сериализатора
            follow = Follow.objects.create(user=request.user, author=author)
            
            # Возвращаем информацию о подписке
            return Response(
                {'status': 'subscribed', 'follow_id': follow.id},
                status=status.HTTP_201_CREATED
            )

        else:  # DELETE
            follow = get_object_or_404(Follow, user=request.user, author=author)
            follow.delete()
            return Response({'status': 'unsubscribed'}, status=status.HTTP_204_NO_CONTENT)

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
