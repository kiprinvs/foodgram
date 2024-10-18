from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models


class User(AbstractUser):
    """Модель пользователя"""

    class RoleChoice(models.TextChoices):
        USER = 'user', 'Пользователь'
        ADMIN = 'admin', 'Администратор'

    username = models.CharField(
        verbose_name='Юзернейм',
        max_length=150,
        unique=True,
        validators=(UnicodeUsernameValidator,),
    )
    email = models.EmailField(
        verbose_name='Почта',
        unique=True
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=150,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=150,
    )
    avatar = models.ImageField(
        verbose_name='Фото',
        upload_to='avatars/',
        blank=True,
        null=True,
    )
    role = models.CharField(
        max_length=150,
        verbose_name='Роль',
        choices=RoleChoice.choices,
        default=RoleChoice.USER,
        blank=True,
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return (
            self.role == self.RoleChoice.ADMIN
            or self.is_superuser
        )


class Subscribe(models.Model):
    """Модель подписки."""

    user = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='subscribers',
    )
    subscribed_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписка'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'subscribed_user'],
                name='unique_user_subscription'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('subscribed_user')),
                name='%(app_label)s_%(class)s_prevent_self_subscribe',
            )
        ]

    def __str__(self):
        return f'{self.user} - {self.subscribed_user}'
