from django.urls import path, re_path

from book import api_views

app_name = "book_api"

urlpatterns = [
    re_path(r"book/$", api_views.BookListApiView.as_view(), name="book-list"),
    re_path(
        r"book/state/$", api_views.BookListStateApiView.as_view(), name="book-state"
    ),
    re_path(
        r"book/(?P<pk>(\d+))/$",
        api_views.BookDetailApiView.as_view(),
        name="book-detail",
    ),
    re_path(
        r"book/(?P<pk>(\d+))/chapter/$",
        api_views.BookChapterListApiView.as_view(),
        name="chapter-list",
    ),
    re_path(
        r"book/chapter/(?P<pk>(\d+))/$",
        api_views.BookChapterDetailApiView.as_view(),
        name="chapter-detail",
    ),
    re_path(
        r"book/subscribe/$",
        api_views.SubscribeBookApiView.as_view(),
        name="subscribe-book",
    ),
    re_path(
        r"book/subscribe/(?P<pk>(\d+))/$",
        api_views.SubscribeBookDetailApiView.as_view(),
        name="subscribe-detail",
    ),
]
