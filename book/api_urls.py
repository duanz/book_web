from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

from book import api_views

app_name = "book_api"

router = DefaultRouter()
router.register(r"book", api_views.BookModelAPIView)
router.register(r"chapter", api_views.BookChapterModelApiView)
router.register(r"subscribe", api_views.SubscribeBookModelApiView)

urlpatterns = [
    re_path(
        r"book/state/$", api_views.BookListStateApiView.as_view(), name="book-state"
    ),
]

urlpatterns += router.urls
