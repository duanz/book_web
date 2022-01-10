from django.urls import path, re_path
from task import api_views

app_name = "task"
urlpatterns = [
    path(r"task/", api_views.TaskApiView.as_view()),
    path(r"task/<int:pk>/", api_views.TaskDetailApiView.as_view()),
    path(r"task/once/", api_views.TaskRunOnceApiView.as_view()),
]
