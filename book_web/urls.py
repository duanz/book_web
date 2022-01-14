"""book_web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import imp
from book import api_urls, api_views
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin, auth
from django.urls import path, re_path
from django.views.static import serve
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers

# router = routers.SimpleRouter()
# router.register(r'^book/chapter/(?P<pk>(\d+))/$',
#                 api_views.BookChapterDetailApiView.as_view., 'chapter-detail')
# router.register(r'', AccountViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="测试工程API",
        default_version="v1.0",
        description="测试工程接口文档",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    # permission_classes=(permissions.AllowAny, ),
)

urlpatterns = [
    path("admin", admin.site.urls),
    path(r"api/v1/", include("book.api_urls", namespace="book_api")),
    path(r"api/v1/", include("task.api_urls")),
    path(r"api/v1/", include("member.api_urls")),
    path(
        r"api/v1/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="api-docs",
    ),
    path(r"api/auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {
            "document_root": settings.MEDIA_ROOT,
        },
    ),
    # 配置drf-yasg路由
]


# urlpatterns += static(settings.MEDIA_ROOT, document_root=settings.MEDIA_ROOT)
