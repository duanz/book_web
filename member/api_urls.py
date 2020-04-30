from django.urls import path
from member import api_views

app_name = "member"
urlpatterns = [
    # user
    path(r'member/info/', api_views.UserDetail.as_view()),
    path(r'member/login/', api_views.UserLoginApiView.as_view()),
    path(r'member/logout/', api_views.UserLogoutApiView.as_view()),
    path(r'member/register/', api_views.UserCreate.as_view()),
]
