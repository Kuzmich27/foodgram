import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from api.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты из CSV-файла в базу данных'

    def handle(self, *args, **options):
        # Путь на уровень выше папки backend
        project_root = os.path.dirname(settings.BASE_DIR)
        data_path = os.path.join(project_root, 'data', 'ingredients.csv')

        if not os.path.exists(data_path):
            self.stderr.write(self.style.ERROR(f'Файл {data_path} не найден'))
            return

        with open(data_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            created_count = 0
            skipped_count = 0

            for row in reader:
                if len(row) != 2:
                    self.stderr.write(self.style.WARNING(f'Пропущена строка: {row}'))
                    continue

                name, unit = row
                obj, created = Ingredient.objects.get_or_create(
                    name=name.strip(),
                    defaults={'unit_of_measurement': unit.strip()}
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Загрузка завершена. Добавлено: {created_count}, пропущено: {skipped_count}'
        ))
