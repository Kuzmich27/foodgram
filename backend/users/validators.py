from django.core.exceptions import ValidationError


def clean_password(self):
    password = self.cleaned_data.get('password')
    username = self.cleaned_data.get('username')

    if (password and username
            and password.lower() == username.lower()):
        return ValidationError('Пароль не должен совпадать с логином')
    return password


def validate_username(username):
    """Функция проверяет, что введенный логин не запрещен для использованию."""
    # Список запрещенных логинов.
    UNALLOWED_LOGINS = (
        'me',
    )

    if username.lower() in UNALLOWED_LOGINS:
        error_message = f'Логин {username} запрещен! Придумайте другой логин.'
        raise ValidationError(error_message)

    return username
