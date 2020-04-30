from django_filters import rest_framework as filters
from book.models import Book, Chapter


class BookListFilter(filters.FilterSet):
    class Meta:
        model = Book
        fields = {
            'title': ['icontains'],
            'author': ['exact'],
        }


class ChapterListFilter(filters.FilterSet):
    class Meta:
        model = Chapter
        fields = {
            'active': ['exact'],
            'number': ['exact'],
            'title': ['icontains'],
            'origin_addr': ['icontains'],
        }
