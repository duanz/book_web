from threading import local
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models.fields.files import FieldFile
from django.views.generic import FormView
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView, BaseListView

from django.shortcuts import render
from django.views.generic.base import View
from book.models import Book
from website.forms import ContactForm, ContactFormSet, FilesForm
from book.serializers import BookSerializer

# http://yuji.wordpress.com/2013/01/30/django-form-field-in-initial-data-requires-a-fieldfile-instance/
class FakeField(object):
    storage = default_storage


fieldfile = FieldFile(None, FakeField, "dummy.txt")


# Create your views here.


class IndexView(TemplateView):
    """首页"""

    template_name = "website/index.html"


class AboutView(TemplateView):
    """关于"""

    template_name = "website/about.html"


class BookMarketView(TemplateView, ListView):
    """书市"""

    template_name = "website/bookmarket.html"
    allow_empty = True
    queryset = Book.objects.filter(on_shelf=True)
    object_list = Book.objects.filter(on_shelf=True)
    model = Book
    # paginate_by = None
    # paginate_orphans = 0
    context_object_name = "books"
    # paginator_class = Paginator
    # page_kwarg = 'page'
    # ordering = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[self.context_object_name] = BookSerializer(
            context[self.context_object_name],
            many=True,
            context={"request": self.request},
        ).data
        return context


class UserCenterView(TemplateView):
    """个人中心"""

    template_name = "website/usercenter.html"


class HomePageView(TemplateView):
    template_name = "website/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        messages.info(self.request, "hello http://example.com")
        return context


# class DefaultFormsetView(FormView):
#     template_name = "website/formset.html"
#     form_class = ContactFormSet


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
