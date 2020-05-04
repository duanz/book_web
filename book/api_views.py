from book.models import Book, Chapter, SubscribeBook
from book.serializers import BookSerializer, BookDetailSerializer, ChapterSerializer, ChapterDetailSerializer, SubscribeBookSerializer
from book.api_filters import ChapterListFilter, BookListFilter
from book_web.utils.permission import IsAuthorization, BaseGenericAPIView, BaseApiView
from rest_framework.permissions import AllowAny, SAFE_METHODS
from rest_framework.response import Response
from rest_framework import mixins
from django_filters import rest_framework


class BookListApiView(mixins.ListModelMixin, BaseGenericAPIView):
    """获取小说列表"""

    queryset = Book.normal.filter()
    serializer_class = BookSerializer

    filter_backends = (rest_framework.DjangoFilterBackend, )
    filter_class = BookListFilter

    ordering_fields = (
        'title',
        'author',
    )

    permission_classes = (AllowAny, )

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class BookListStateApiView(mixins.ListModelMixin, BaseGenericAPIView):
    """获取小说统计列表
    state_type: 
        new:    最近新增的30本
        subscribe:    订阅最多的30本
    """

    queryset = Book.normal.filter()
    serializer_class = BookSerializer

    filter_backends = (rest_framework.DjangoFilterBackend, )
    filter_class = BookListFilter

    permission_classes = (AllowAny, )

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        state_type = self.request.GET['state_type']
        if state_type == 'new':
            books = self.state_new()
        elif state_type == 'subscribe':
            books = self.state_subscribe()
        return books

    def state_new(self):
        books = Book.normal.filter().order_by('-create_at')[:30]
        return books

    def state_subscribe(self):
        books = Book.normal.filter().order_by('-click_num')[:30]
        return books


class BookDetailApiView(mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                        BaseGenericAPIView):
    """
    get: 获取小说详情；
    """
    queryset = Book.normal.filter(on_shelf=True)
    serializer_class = BookDetailSerializer
    permission_classes = (AllowAny, )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [permission() for permission in self.permission_classes]
        else:
            return [IsAuthorization()]


class BookChapterDetailApiView(mixins.RetrieveModelMixin, BaseGenericAPIView):
    """
    get: 获取小说章节详情
    """
    queryset = Chapter.normal.filter(active=True)
    serializer_class = ChapterDetailSerializer
    permission_classes = (AllowAny, )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class BookChapterListApiView(mixins.ListModelMixin, BaseGenericAPIView):
    """
    get: 获取小说章节列表；
    """
    queryset = Chapter.normal.filter(active=True)
    serializer_class = ChapterSerializer

    filter_backends = (rest_framework.DjangoFilterBackend, )
    filter_class = ChapterListFilter

    permission_classes = (AllowAny, )

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return self.queryset.filter(book__id=self.kwargs['pk'])


class SubscribeBookApiView(mixins.CreateModelMixin, mixins.ListModelMixin,
                           BaseGenericAPIView):
    """
    get: 获取订阅；
    post: 添加订阅；
    """
    queryset = SubscribeBook.normal.filter()
    serializer_class = SubscribeBookSerializer
    permission_classes = (IsAuthorization, )

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def get_queryset(self):
        print(self.request.user)
        return self.queryset.filter(user__id=self.request.user.id)


class SubscribeBookDetailApiView(mixins.DestroyModelMixin,
                                 mixins.UpdateModelMixin,
                                 mixins.RetrieveModelMixin,
                                 BaseGenericAPIView):
    """
    get: 获取订阅详情；
    put: 修改订阅；
    delete: 删除订阅；
    """
    queryset = SubscribeBook.normal.filter()
    serializer_class = SubscribeBookSerializer
    permission_classes = (IsAuthorization, )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def get_queryset(self):
        print(self.request.user)
        return self.queryset.filter(user__id=self.request.user.id)
