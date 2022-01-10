from django_filters import rest_framework as filters
from book.models import Book, Chapter


class BookListFilter(filters.FilterSet):
    state_type = filters.CharFilter(method="search_state_type", label="")

    class Meta:
        model = Book
        fields = {
            "title": ["icontains"],
            "author": ["exact"],
        }

    def search_state_type(self, qs, name, value):
        label = "-update_at"
        if value == "new":
            label = "-create_at"
        elif value == "subscribe":
            label = "-click_num"
        return qs.order_by(label)


class ChapterListFilter(filters.FilterSet):
    class Meta:
        model = Chapter
        fields = {
            "active": ["exact"],
            "number": ["exact"],
            "title": ["icontains"],
            "origin_addr": ["icontains"],
        }
