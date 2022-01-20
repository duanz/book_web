from django.urls import path

from website.views import IndexView, AboutView, UserCenterView, BookMarketView

app_name = "website"

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("about", AboutView.as_view(), name="about"),
    path("bookmarket", BookMarketView.as_view(), name="bookmarket"),
    path("usercenter", UserCenterView.as_view(), name="usercenter"),
    # path("", HomePageView.as_view(), name="home"),
    # path("formset", DefaultFormsetView.as_view(), name="formset_default"),
    # path("form", DefaultFormView.as_view(), name="form_default"),
    # path("form_by_field", DefaultFormByFieldView.as_view(), name="form_by_field"),
    # path("form_horizontal", FormHorizontalView.as_view(), name="form_horizontal"),
    # path("form_inline", FormInlineView.as_view(), name="form_inline"),
    # path("form_with_files", FormWithFilesView.as_view(), name="form_with_files"),
    # path("pagination", PaginationView.as_view(), name="pagination"),
    # path("misc", MiscView.as_view(), name="misc"),
]
