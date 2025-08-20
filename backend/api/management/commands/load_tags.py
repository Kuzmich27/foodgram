import os
from django.core.management.base import BaseCommand
from api.models import Tag


class Command(BaseCommand):
    help = 'Создаёт стандартные теги для рецептов'

    DEFAULT_TAGS = [
        ('Завтрак', 'breakfast'),
        ('Обед', 'lunch'),
        ('Ужин', 'dinner'),
    ]

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for name, slug in self.DEFAULT_TAGS:
            obj, created = Tag.objects.get_or_create(
                name=name,
                defaults={'slug': slug}
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Загрузка тегов завершена. Добавлено: {created_count}, пропущено: {skipped_count}'
        ))
