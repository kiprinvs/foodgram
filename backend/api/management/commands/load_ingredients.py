import json
import os

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        if not os.path.isfile(file_path):
            self.stdout.write(
                self.style.ERROR(f'File "{file_path}" does not exist.')
            )
            return

        with open(file_path, 'r', encoding='utf-8') as file:
            ingredients_data = json.load(file)

        for ingredient in ingredients_data:
            Ingredient.objects.create(
                name=ingredient['name'],
                measurement_unit=ingredient['measurement_unit']
            )

        self.stdout.write(self.style.SUCCESS(
            'Ingredients loaded successfully!')
        )
