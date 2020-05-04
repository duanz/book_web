from django.contrib import admin
from book.models import Book, Chapter, ChapterImage, Image


# Register your models here.
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('id', 'book_type', 'title', 'origin_addr')


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('id', 'book_type', 'book', 'order', 'title', 'origin_addr')


@admin.register(ChapterImage)
class ChapterImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'book', 'chapter', 'image')


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'key', 'img_type')
