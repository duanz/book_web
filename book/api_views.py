from book.models import Book, Chapter, SubscribeBook
from book.serializers import (
    BookSerializer,
    BookDetailSerializer,
    ChapterSerializer,
    ChapterDetailSerializer,
    SubscribeBookSerializer,
)
from book.api_filters import ChapterListFilter, BookListFilter
from book_web.utils.permission import (
    IsAuthorization,
    GenericAPIView,
    GenericModelViewSet,
)
from rest_framework.permissions import AllowAny, SAFE_METHODS
from rest_framework.response import Response
from rest_framework import mixins
from rest_framework.views import APIView
from django_filters import rest_framework
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class BookModelAPIView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericModelViewSet,
):
    """获取小说列表"""

    queryset = Book.normal.filter()
    serializer_class = BookSerializer

    filter_backends = (rest_framework.DjangoFilterBackend,)
    filter_class = BookListFilter

    ordering_fields = (
        "title",
        "author",
    )

    permission_classes = (AllowAny,)

    def get_queryset(self):
        if not self.request.user.is_staff:
            self.queryset = self.queryset.filter(on_shelf=True)
        return self.queryset

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [permission() for permission in self.permission_classes]
        else:
            return [IsAuthorization()]


class BookListStateApiView(mixins.ListModelMixin, GenericAPIView):
    """获取小说统计列表
    state_type:
        new:    最近新增的30本
        subscribe:    订阅最多的30本
    """

    queryset = Book.normal.filter()
    serializer_class = BookSerializer

    filter_backends = (rest_framework.DjangoFilterBackend,)
    filter_class = BookListFilter

    permission_classes = (AllowAny,)

    @method_decorator(cache_page(60 * 30))
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        if not self.request.user.is_staff:
            self.queryset = self.queryset.filter(on_shelf=True)
        return self.queryset


class BookChapterModelApiView(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericModelViewSet
):
    """
    get: 获取小说章节详情
    get: 获取小说章节列表；
    """

    queryset = Chapter.normal.filter()
    serializer_class = ChapterSerializer

    filter_backends = (rest_framework.DjangoFilterBackend,)
    filter_class = ChapterListFilter

    permission_classes = (AllowAny,)

    def get_queryset(self):
        if not self.request.user.is_staff:
            self.queryset = self.queryset.filter(active=True)

        return (
            self.queryset.filter(book__id=self.kwargs["pk"])
            if "pk" in self.kwargs
            else self.queryset
        )


class SubscribeBookModelApiView(
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericModelViewSet,
):
    """
    get: 获取订阅详情；
    put: 修改订阅；
    delete: 删除订阅；
    get: 获取订阅；
    post: 添加订阅；
    """

    queryset = SubscribeBook.normal.filter()
    serializer_class = SubscribeBookSerializer
    permission_classes = (IsAuthorization,)

    def get_queryset(self):
        print(self.request.user)
        return self.queryset.filter(user__id=self.request.user.id)
