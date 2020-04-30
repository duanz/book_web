from django.contrib.auth import authenticate, login, logout
from django_filters import rest_framework
from rest_framework import filters, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import SAFE_METHODS, AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from book_web.utils.permission import IsAuthorization, BaseApiView, BaseGenericAPIView
from django.contrib.auth.models import User
from member.serializers import UserSerializer, UserLoginSerializer


class UserCreate(mixins.CreateModelMixin, BaseGenericAPIView):
    '''
    post: 添加用户.
    '''

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (AllowAny, )

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class UserDetail(mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                 mixins.DestroyModelMixin, BaseGenericAPIView):
    '''
    get: 获取用户信息；
    put: 更新用户；
    delete: 删除用户。
    '''

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthorization, )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        kwargs.update({'partial': True})
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def get_object(self):
        return User.objects.filter(pk=self.request.user.id).first()


class UserLoginApiView(BaseApiView):
    '''post: 使用用户名密码登录'''

    queryset = User.objects.all()
    serializer_class = UserLoginSerializer
    permission_classes = (AllowAny, )
    authentication_classes = (TokenAuthentication, )

    def post(self, request, format=None):
        data = request.data
        username = data.get('username')
        password = data.get('password')
        print(username, password)
        user = authenticate(username=username, password=password)
        print(user)
        if user is not None and user.is_active:
            user.ip_address = request.META.get('REMOTE_ADDR')
            user.save()
            login(request, user)
            serializer = UserSerializer(user, context={'request': request})
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(
            {
                'msg': '用户名或密码错误',
                'code': HTTP_400_BAD_REQUEST,
                'result': 'FAIL'
            },
            status=HTTP_200_OK)

    def perform_authentication(self, request):
        """
        重写父类的用户验证方法，不在进入视图前就检查JWT
        """
        pass


class UserLogoutApiView(BaseApiView):
    '''post: 注销登录'''

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthorization, )

    def post(self, request, format=None):
        logout(request)
        return Response(
            {
                'msg': '退出成功',
                'code': HTTP_200_OK,
                'result': 'SUCCESS'
            },
            status=HTTP_200_OK)
