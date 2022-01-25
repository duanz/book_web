from threading import local
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models.fields.files import FieldFile
from django.views.generic import FormView
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView, BaseListView
from django.http.request import QueryDict
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.views.generic.base import View
from book.models import Book, Chapter
from website.forms import ContactForm, ContactFormSet, FilesForm, LoginForm
from book.serializers import (
    BookDetailSerializer,
    BookSerializer,
    ChapterDetailSerializer,
    ChapterSerializer,
)

# http://yuji.wordpress.com/2013/01/30/django-form-field-in-initial-data-requires-a-fieldfile-instance/
class FakeField(object):
    storage = default_storage


fieldfile = FieldFile(None, FakeField, "dummy.txt")


# Create your views here.


class IndexView(BaseListView, TemplateView):
    """首页"""

    template_name = "website/index.html"

    allow_empty = True
    queryset = Chapter.objects.filter(
        book_id__in=Book.objects.filter(markup="新闻").values_list("id", flat=True)
    )
    # object_list = Book.objects.filter(on_shelf=True)
    model = Chapter
    paginate_by = 20
    # paginate_orphans = 0
    context_object_name = "chapters"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[self.context_object_name] = ChapterSerializer(
            context[self.context_object_name],
            many=True,
            context={"request": self.request, "quality": "thumbicon"},
        ).data
        return context


class AboutView(TemplateView):
    """关于"""

    template_name = "website/about.html"


class BookMarketView(BaseListView, TemplateView):
    """书市"""

    template_name = "website/bookmarket.html"
    allow_empty = True
    queryset = Book.objects.filter()
    # object_list = Book.objects.filter(on_shelf=True)
    model = Book
    paginate_by = 15
    # paginate_orphans = 0
    context_object_name = "books"
    # paginator_class = Paginator
    # page_kwarg = 'page'
    # ordering = None

    def build_url_query_string(self, popkey: list):
        query_parmas = ""
        for key, val in self.request.GET.items():
            if key not in popkey:
                query_parmas += f"&{key}={val}"
        query_parmas = query_parmas.removeprefix("&")
        return query_parmas

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["fixed_url"] = self.build_url_query_string(["page"])
        context[self.context_object_name] = BookSerializer(
            context[self.context_object_name],
            many=True,
            context={"request": self.request, "quality": "thumbicon"},
        ).data
        context["hotbooks"] = BookSerializer(
            Book.objects.filter(on_shelf=True).order_by("-click_num")[:10],
            many=True,
            context={"request": self.request, "quality": "thumbicon"},
        ).data
        if not cache.get("book_labels"):
            cache.set(
                "book_labels",
                set(Book.objects.filter().values_list("markup", flat=True)),
                60 * 60 * 24 * 1,
            )
        context["labels"] = cache.get("book_labels")
        return context

    def get_queryset(self):
        print(self.request.GET)
        qs = super().get_queryset()
        if markup := self.request.GET.get("markup"):
            qs = qs.filter(markup=markup)
        if title := self.request.GET.get("title"):
            qs = qs.filter(title__icontains=title)

        print(qs.count())
        return qs


class BookInfoView(TemplateView):
    """书籍详情"""

    template_name = "website/bookinfo.html"

    def get_context_data(self, **kwargs):
        print(kwargs)
        context = super().get_context_data(**kwargs)
        context["book"] = BookDetailSerializer(
            Book.objects.get(id=kwargs.get("pk")),
            context={"request": self.request, "quality": "title"},
        ).data
        return context


class ChapterDetailView(TemplateView):
    """章节详情"""

    template_name = "website/chapter_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["chapter"] = ChapterDetailSerializer(
            Chapter.objects.get(id=kwargs.get("pk")),
            context={"request": self.request, "quality": "title"},
        ).data
        return context


class UserCenterView(TemplateView):
    """个人中心"""

    template_name = "website/usercenter.html"

    def post(self, *args, **kwargs):
        logout(self.request)
        return redirect("website:index")


class LoginView(TemplateView):
    """登录页面"""

    template_name = "website/login.html"

    def post(self, *args, **kwargs):
        username = self.request.POST.get("username")
        password = self.request.POST.get("password")
        user = authenticate(username=username, password=password)
        context = self.get_context_data(**kwargs)

        if user is not None:
            if user.is_active:
                login(self.request, user)
                # 跳转到成功页面.
                return redirect("website:usercenter")
            else:
                # 返回一个无效帐户的错误
                context["error"] = "账号未激活"
        else:
            context["error"] = "用户名或密码错误"
            # 返回登录失败页面。
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = LoginForm()
        return context


class HomePageView(TemplateView):
    template_name = "website/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        messages.info(self.request, "hello http://example.com")
        return context


class DefaultFormsetView(FormView):
    template_name = "website/login.html"
    form_class = ContactFormSet


# class DefaultFormView(FormView):
#     template_name = "website/form.html"
#     form_class = ContactForm


# class DefaultFormByFieldView(FormView):
#     template_name = "website/form_by_field.html"
#     form_class = ContactForm


# class FormHorizontalView(FormView):
#     template_name = "website/form_horizontal.html"
#     form_class = ContactForm


# class FormInlineView(FormView):
#     template_name = "website/form_inline.html"
#     form_class = ContactForm


# class FormWithFilesView(FormView):
#     template_name = "website/form_with_files.html"
#     form_class = FilesForm

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context["layout"] = self.request.GET.get("layout", "vertical")
#         return context

#     def get_initial(self):
#         return {"file4": fieldfile}


# class PaginationView(TemplateView):
#     template_name = "website/pagination.html"

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         lines = []
#         for i in range(200):
#             lines.append("Line %s" % (i + 1))
#         paginator = Paginator(lines, 10)
#         page = self.request.GET.get("page")
#         try:
#             show_lines = paginator.page(page)
#         except PageNotAnInteger:
#             # If page is not an integer, deliver first page.
#             show_lines = paginator.page(1)
#         except EmptyPage:
#             # If page is out of range (e.g. 9999), deliver last page of results.
#             show_lines = paginator.page(paginator.num_pages)
#         context["lines"] = show_lines
#         return context


# class MiscView(TemplateView):
#     template_name = "website/misc.html"
