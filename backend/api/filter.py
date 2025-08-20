import django_filters
from django_filters import CharFilter, FilterSet

from api.models import Recipe


class RecipeFilter(FilterSet):
    """Филтьрация модели Recipe по различным полям объектов."""

    class Meta:
        model = Recipe
        fields = (
            'tags',
        )
