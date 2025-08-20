from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator, RegexValidator

from users.validators import validate_username
from api.constants import (
    EMAIL_MAX_LENGHT,
    USERNAME_MAX_LENGHT,
    LOGIN_ERROR_MESSAGE,
    FIRST_NAME_MAX_LENGHT,
    LAST_NAME_MAX_LENGHT
)


class CustomUser(AbstractUser):
    """Модель для создания пользователя Users."""

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='Группы',
        blank=True,
        help_text='Группы, к которым принадлежит пользователь',
        related_name='customuser_set',
        related_query_name='customuser',
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='Права пользователя',
        blank=True,
        help_text='Конкретные права для этого пользователя',
        related_name='customuser_set',
        related_query_name='customuser',
    )

    username = models.CharField(
        verbose_name='Логин',
        unique=True,
        max_length=USERNAME_MAX_LENGHT,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message=LOGIN_ERROR_MESSAGE
            ),
            validate_username,
        ]
    )

    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        max_length=EMAIL_MAX_LENGHT,
        unique=True,
        validators=[EmailValidator()]
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        verbose_name='Аватар',
        blank=True,
        null=True
    )

    first_name = models.CharField(
        verbose_name='Имя',
        max_length=FIRST_NAME_MAX_LENGHT,
        blank=True,
    )

    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=LAST_NAME_MAX_LENGHT,
        blank=True,
    )

    bio = models.TextField(
        verbose_name='Информация о пользователе',
        blank=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('id',)

    def __str__(self):
        return self.email
