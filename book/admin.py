from django.contrib import admin
from book.models import Book, Chapter, ChapterImage, Image
from task.models import Task
from django.shortcuts import resolve_url
from django.utils.html import format_html
from task.tasks import async_model_task

# Register your models here.


@admin.action(description="书籍更新章节信息")
def book_update_chapter_without_content(modeladmin, request, queryset):
    task_ids = []
    for book in queryset:
        task_ids.append(Task.create_task_for_book_update(request.user.id, book.id).id)
    async_model_task(task_ids)


@admin.action(description="书籍打包")
def make_book(modeladmin, request, queryset):
    task_ids = []
    for book in queryset:
        task_ids.append(Task.create_task_for_make_book(request.user.id, book.id).id)
    async_model_task(task_ids)


@admin.action(description="书籍更新章节内容信息")
def book_update_chapter_with_content(modeladmin, request, queryset):
    task_ids = []
    for book in queryset:
        task_ids.append(
            Task.create_task_for_book_update(
                request.user.id, book.id, update_type="with_content"
            ).id
        )
    async_model_task(task_ids)


@admin.action(description="更新章节内容信息")
def update_chapter_with_content(modeladmin, request, queryset):
    task_ids = []
    for chapter in queryset:
        task_ids.append(
            Task.create_task_for_book_update(
                request.user.id, chapter_id=chapter.id, update_type="with_content"
            ).id
        )
    async_model_task(task_ids)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "id", "book_type", "origin_addr", "operator")
    search_fields = ("title", "id")
    list_filter = ("book_type", "update_at")
    date_hierarchy = "create_at"

    actions = [
        book_update_chapter_without_content,
        book_update_chapter_with_content,
        make_book,
    ]

    def operator(self, obj):
        link = resolve_url("admin:book_chapter_changelist")
        return format_html(f"<a href='{link}?q={obj.title}'>查看章节</a>")

    operator.allow_tags = True


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("title", "id", "book_type", "book_", "order", "origin_addr")
    search_fields = ("title", "book__title", "id")
    list_filter = ("active", "book_type", "update_at")
    actions = [update_chapter_with_content]

    def book_(self, obj):
        link = resolve_url("admin:book_book_change", obj.book.id)
        return format_html(f"<a href='{link}'>{obj.book.title}</a>")

    book_.allow_tags = True


@admin.register(ChapterImage)
class ChapterImageAdmin(admin.ModelAdmin):
    list_display = ("id", "book", "chapter", "image")


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "key", "img_type")
