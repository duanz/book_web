#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Date    : 2018/7/6 11:31
# @Author  : duan
# @FileName: permission.py
# @Desc :

from typing import Generic
from rest_framework import permissions, authentication, exceptions, status
from rest_framework.response import Response
from rest_framework import mixins, generics, views, viewsets
from rest_framework.viewsets import ViewSetMixin


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


class GenericModelViewSet(ViewSetMixin, generics.GenericAPIView):
    pass


class GenericAPIView(views.APIView):
    pass


def handle_response_exception(response):
    code = response.status_code
    data = response.data
    first_msg = list(data.keys())[0]
    msg = data.get(first_msg) if first_msg else "信息错误"
    return {"code": code, "data": data, "msg": msg, "result": "FAIL"}
