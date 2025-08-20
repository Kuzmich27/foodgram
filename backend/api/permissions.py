from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Разрешение: редактировать объект может только его автор или администратор.
    Для чтения доступ открыт всем.
    """
    def has_object_permission(self, request, view, obj):
        # Любой может читать
        if request.method in permissions.SAFE_METHODS:
            return True
        # Только автор или админ могут редактировать/удалять
        return (
            obj.author == request.user
            or request.user.is_staff
            or request.user.is_superuser
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Разрешение: изменения может вносить только администратор.
    Для чтения доступ открыт всем.
    """
    def has_permission(self, request, view):
        # Разрешаем GET, HEAD, OPTIONS всем
        if request.method in permissions.SAFE_METHODS:
            return True
        # Изменять может только администратор
        return request.user.is_staff or request.user.is_superuser
