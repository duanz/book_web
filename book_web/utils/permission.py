#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Date    : 2018/7/6 11:31
# @Author  : duan
# @FileName: permission.py
# @Desc :

from rest_framework import permissions, authentication, exceptions, status
from rest_framework.response import Response
from rest_framework import mixins, generics, views


# 拥有者可操作或只读
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner.id == request.user.id


# 需要登录或只读
class IsAuthorizationOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


# 需要登录
class IsAuthorization(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


# 自定义异常的响应
class BaseApiView(views.APIView):
    def handle_exception(self, exc):
        """
        Handle any exception that occurs, by returning an appropriate response,
        or re-raising the error.
        """
        if isinstance(exc, (exceptions.NotAuthenticated,
                            exceptions.AuthenticationFailed)):
            # WWW-Authenticate header for 401 responses, else coerce to 403
            auth_header = self.get_authenticate_header(self.request)

            if auth_header:
                exc.auth_header = auth_header
            else:
                exc.status_code = status.HTTP_403_FORBIDDEN

        exception_handler = self.get_exception_handler()

        context = self.get_exception_handler_context()
        response = exception_handler(exc, context)

        if response is None:
            self.raise_uncaught_exception(exc)

        response.exception = True
        response.data = handle_response_exception(response)
        response.status_code = status.HTTP_200_OK
        return response


# 自定义异常的响应
class BaseGenericAPIView(generics.GenericAPIView):
    def handle_exception(self, exc):
        """
        Handle any exception that occurs, by returning an appropriate response,
        or re-raising the error.
        """
        if isinstance(exc, (exceptions.NotAuthenticated,
                            exceptions.AuthenticationFailed)):
            # WWW-Authenticate header for 401 responses, else coerce to 403
            auth_header = self.get_authenticate_header(self.request)

            if auth_header:
                exc.auth_header = auth_header
            else:
                exc.status_code = status.HTTP_403_FORBIDDEN

        exception_handler = self.get_exception_handler()

        context = self.get_exception_handler_context()
        response = exception_handler(exc, context)

        if response is None:
            self.raise_uncaught_exception(exc)

        response.exception = True
        response.data = handle_response_exception(response)
        response.status_code = status.HTTP_200_OK
        return response


def handle_response_exception(response):
    code = response.status_code
    data = response.data
    first_msg = list(data.keys())[0]
    msg = data.get(first_msg) if first_msg else '信息错误'
    return {'code': code, 'data': data, 'msg': msg, 'result': 'FAIL'}
