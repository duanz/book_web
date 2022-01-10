# import mkepub
# import os
# import shutil
# from book_web.utils.base_logger import logger

# from comic_admin.models import Comic, ChapterImage
# from comic_admin.models import Chapter as ComicChapter
# from book_admin.models import Book, Author
# from book_admin.models import Chapter as BookChapter
# from comic_admin.serializers import CommonImageSerializer
# from django.conf import settings
# from comic_web.utils.photo import split_photo_fit_kindle

# class MakeMyEpub:
#     def __init__(self, content_id, content_type):
#         self.content_id = content_id
#         self.content_type = content_type
#         self.title = ""
#         self.filename = ""

#     def run(self):
#         if self.content_type == "comic":
#             self.makeComicEpub()
#         elif self.content_type == 'book':
#             self.makeBookEpub()
#         pass

#     def makeComicEpub(self):
#         comic_id = self.content_id
#         comic_obj = Comic.normal.filter(id=comic_id).first()
#         self.title = comic_obj.title

#         # 初始化epub
#         epub = mkepub.Book(title=comic_obj.title, author=str(comic_obj.author))
#         logging.info("epub 已经初始化")

#         # 设置封面
#         comic_cover_path_list = CommonImageSerializer.to_representation(comic_id=comic_id, img_type="comic_cover", quality="title", only_url=False, only_path=True)
#         logging.info(comic_cover_path_list)
#         if comic_cover_path_list:
#             with open(comic_cover_path_list[0], 'rb') as file:
#                 epub.set_cover(file.read())
#         logging.info("epub 设置封面完成")

#         # 设置章节
#         chapters = ComicChapter.normal.filter(comic_id=comic_id)
#         for chapter in chapters:
#             html = ""
#             img_lab = '<img src="images/{}" width="100%" alt="You can use images as well">'
#             chapter_img_path_list = CommonImageSerializer.to_representation(chapter_id=chapter.id, img_type="chapter_content", quality="thumb", only_url=False, only_path=True)
#             if chapter_img_path_list:
#                 for img_idx, img_path in enumerate(chapter_img_path_list):
#                     file_name = "{}_{}_{}.jpg".format(comic_id, chapter.id, img_idx)
#                     html+=img_lab.format(file_name)
#                     with open(img_path, 'rb') as file:
#                         epub.add_image(file_name, file.read())
#             epub.add_page(chapter.title, html)

#         logging.info("epub 完成")
#         filename = os.path.join(settings.MEDIA_ROOT, comic_obj.title + '.epub')
#         if os.path.exists(filename):
#             os.remove(filename)
#         self.filename = filename
#         epub.save(filename)
#         comic_obj.is_download = True
#         comic_obj.save()

#     def makeBookEpub(self):
#         book_id = self.content_id
#         book_obj = Book.normal.filter(id=book_id).first()
#         self.title = book_obj.title

#         # 初始化epub
#         epub = mkepub.Book(title=book_obj.title, author=str(book_obj.author))

#         # 设置封面
#         book_cover_path_list = CommonImageSerializer.to_representation(book_id=book_id, img_type="book_cover", only_url=False, only_path=True)
#         if book_cover_path_list:
#             with open(book_cover_path_list[0], 'rb') as file:
#                 epub.set_cover(file.read())

#         # 设置章节
#         chapters = BookChapter.normal.filter(book_id=book_id)
#         for chapter in chapters:
#             epub.add_page(chapter.title, chapter.content)


#         filename = os.path.join(settings.MEDIA_ROOT, book_obj.title + '.epub')
#         self.filename = filename
#         epub.save(filename)
#         book_obj.is_download = True
#         book_obj.save()
class MakeMyEpub:
    raise NotImplementedError
