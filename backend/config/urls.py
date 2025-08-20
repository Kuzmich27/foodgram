from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API роуты твоего приложения
    path('api/', include('api.urls')),

    # Djoser — регистрация, логин, смена пароля и т.п.
    path('api/auth/', include('djoser.urls.authtoken')),
    path('api/auth/', include('djoser.urls')),
]

# Подключаем медиа в DEBUG
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Фронтенд рендерим на все остальные URL, кроме admin и api
urlpatterns += [
    re_path(r'^(?!admin/|api/).*$', TemplateView.as_view(
        template_name='index.html')),
]
