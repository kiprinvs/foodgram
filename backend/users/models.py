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

    class Meta:
        verbose_name = 'Пользователь',
        verbose_name_plural = 'Пользователи',
        ordering = ('username',)

    def __str__(self):
        return f'{self.username} - {self.email}'

    @property
    def is_admin(self):
        return (
            self.role == self.RoleChoice.ADMIN
            or self.is_superuser
        )


class Follow(models.Model):
    """Модель подписки."""

    user = models.ForeignKey(
        User,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='followers',
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follows',
        verbose_name='Подписка'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='unique_user_following'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('following')),
                name='%(app_label)s_%(class)s_prevent_self_follow',
            )
        ]

    def __str__(self):
        return f'{self.user} - {self.following}'
