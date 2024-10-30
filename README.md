# FOODGRAM
Сайт доступен по адресу: https://swr-foodgram.sytes.net

## Описание проекта
Foodgram — это веб-приложение для управления рецептами, которое позволяет пользователям создавать, хранить и делиться рецептами. Приложение предоставляет удобный интерфейс для добавления новых рецептов, управления ингредиентами и тегами, а также для формирования списков покупок.
### Основные функции:
Создание и редактирование рецептов: Пользователи могут добавлять новые рецепты с описанием, временем приготовления, изображениями и списком ингредиентов.
Система тегов: Упрощает поиск рецептов по категориям, таким как "Завтрак", "Ужин" и т.д.
Избранные рецепты: Пользователи могут добавлять рецепты в избранное для быстрого доступа.
Список покупок: Пользователи могут формировать списки покупок на основе выбранных рецептов.

### Инструкция как развернуть в докере
1. Убедитесь, что на вашем компьютере установлены Docker и Docker Compose.
2. Клонирование репозитория
```
git clone https://github.com/kiprinvs/foodgram.git
```
3. Перейти в папку проекта
```
cd foodgram
```
4. Запустите Docker Compose
```
docker-compose up
```
5. Откройте приложение
```
http://localhost:8000
```

### Стек технологий
Python: Используется в качестве основного языка программирования для разработки бэкенда.
Django: Веб-фреймворк для создания веб-приложений и API.
Django REST Framework: Библиотека для создания RESTful API на основе Django.
PostgreSQL: Реляционная база данных, используемая для хранения данных приложения.
Nginx: Веб-сервер, используемый для проксирования запросов и обслуживания статических файлов.
Docker: Платформа для контейнеризации, позволяющая легко развертывать и управлять приложением.
Docker Compose: Инструмент для определения и запуска многоконтейнерных Docker приложений.
GitHub Actions: Система CI/CD для автоматизации сборки, тестирования и развертывания приложения.

### Как наполнить БД данными
Добавление ингредиентов
```
docker compose exec backend python manage.py loaddata initial_data.json
```

### Документация к API
Документация доступна по эндпоинту
```
http://localhost/api/docs/
```


### Пример запросов/ответов
Пример запроса на создание рецепта
 ```
http://localhost/api/recipes/
```
```
{
    "ingredients": [
        {
            "id": 1123,
            "amount": 10
        }
    ],
    "tags": [
        1,
        2
    ],
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
    "name": "string",
    "text": "string",
    "cooking_time": 1
}
```

Пример ответа
```
{
    "id": 0,
    "tags": [
        {
            "id": 0,
            "name": "Завтрак",
            "slug": "breakfast"
        }
    ],
    "author": {
        "email": "user@example.com",
        "id": 0,
        "username": "string",
        "first_name": "Вася",
        "last_name": "Иванов",
        "is_subscribed": false,
        "avatar": "http://foodgram.example.org/media/users/image.png"
    },
    "ingredients": [
        {
            "id": 0,
            "name": "Картофель отварной",
            "measurement_unit": "г",
            "amount": 1
        }
    ],
    "is_favorited": true,
    "is_in_shopping_cart": true,
    "name": "string",
    "image": "http://foodgram.example.org/media/recipes/images/image.png",
    "text": "string",
    "cooking_time": 1
}
```