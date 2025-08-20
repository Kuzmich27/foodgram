from rest_framework.pagination import PageNumberPagination


class RecipePagination(PageNumberPagination):
    """Пагинация для страниц с рецептами."""

    page_size = 6
    page_size_query_param = 'limit'


class RecipeIngredientPagination(PageNumberPagination):
    """Пагинация для страниц с рецептами."""

    page_size = 6


class SubscriptionPagination(PageNumberPagination):
    """Пагинация для страниц с подписками."""

    page_size = 6
