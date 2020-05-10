from django.contrib.auth import authenticate, login, logout
from django_filters import rest_framework
from rest_framework import filters, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import SAFE_METHODS, AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from book_web.utils.permission import IsAuthorization, BaseApiView, BaseGenericAPIView
from task.models import Task
from task.serializers import TaskSerializer
from task.tasks import once_auto_insert_books


class TaskApiView(mixins.ListModelMixin, mixins.CreateModelMixin,
                  BaseGenericAPIView):
    """
    get: 获取任务列表
    post: 添加任务
    """
    queryset = Task.normal.filter()
    serializer_class = TaskSerializer
    permission_classes = (IsAuthorization, )

    def get(self, request, *args, **kwargs):
        from task.tasks import auto_update_books
        auto_update_books.delay()
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [permission() for permission in self.permission_classes]
        else:
            return [IsAuthorization()]


class TaskDetailApiView(mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                        mixins.DestroyModelMixin, BaseGenericAPIView):
    """
    get: 获取任务详情
    post: 修改任务
    delete: 删除任务
    """
    queryset = Task.normal.filter()
    serializer_class = TaskSerializer
    permission_classes = (AllowAny, )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [permission() for permission in self.permission_classes]
        else:
            return [IsAuthorization()]


class TaskRunOnceApiView(BaseGenericAPIView):
    """
    get: 执行只运行一次的任务
    """
    permission_classes = (IsAuthorization, )

    def get(self, request, *args, **kwargs):
        once_auto_insert_books.delay()
        return Response(data="下发成功", status=HTTP_200_OK)
