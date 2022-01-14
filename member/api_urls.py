from django.urls import path
from member import api_views
from rest_framework.routers import DefaultRouter

routers = DefaultRouter()
routers.register("member", api_views.UserModelApiView)
routers.register("activecode", api_views.ActiveCodeModelApiView)

app_name = "member"
urlpatterns = [
    # user
    path(r"member/login/", api_views.UserLoginApiView.as_view()),
    path(r"member/logout/", api_views.UserLogoutApiView.as_view()),
]

urlpatterns += routers.urls
