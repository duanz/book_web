from django.urls import path
from django.conf.urls import url

from book import api_views

app_name = "book_api"

urlpatterns = [
    url(r'^book/$', api_views.BookListApiView.as_view(), name='book-list'),
    url(r'^book/(?P<pk>(\d+))/$',
        api_views.BookDetailApiView.as_view(),
        name='book-detail'),
    url(r'^book/(?P<pk>(\d+))/chapter/$',
        api_views.BookChapterListApiView.as_view(),
        name='chapter-list'),
    url(r'^book/chapter/(?P<pk>(\d+))/$',
        api_views.BookChapterDetailApiView.as_view(),
        name='chapter-detail'),
    url(r'^book/subscribe/$',
        api_views.SubscribeBookApiView.as_view(),
        name='subscribe-book'),
    url(r'^book/subscribe/(?P<pk>(\d+))/$',
        api_views.SubscribeBookDetailApiView.as_view(),
        name='subscribe-detail')
]
