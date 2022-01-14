from django.urls import path, re_path
from task import api_views
from rest_framework.routers import DefaultRouter

routers = DefaultRouter()
routers.register("task", api_views.TaskApiView)
app_name = "task"
urlpatterns = [
    path(r"task/once/", api_views.TaskRunOnceApiView.as_view()),
]

urlpatterns += routers.urls
