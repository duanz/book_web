from django.contrib import admin
from book.models import Book, Chapter, ChapterImage, Image
from task.models import Task

from task.tasks import async_model_task

# Register your models here.


@admin.action(description="书籍更新章节信息")
def book_update_chapter_without_content(modeladmin, request, queryset):
    task_ids = []
    for book in queryset:
        task_ids.append(Task.create_task_for_book_update(request.user.id, book.id).id)
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
    list_display = ("id", "book_type", "title", "origin_addr")
    search_fields = ("title",)
    list_filter = ("book_type", "update_at")
    actions = [book_update_chapter_without_content, book_update_chapter_with_content]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("id", "book_type", "book", "order", "title", "origin_addr")
    search_fields = ("title",)
    list_filter = ("book_type", "update_at")
    actions = [update_chapter_with_content]


@admin.register(ChapterImage)
class ChapterImageAdmin(admin.ModelAdmin):
    list_display = ("id", "book", "chapter", "image")


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "key", "img_type")
