import os
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from book_web.utils.base_model import BaseModel
from book_web.utils import photo as photo_lib
from book_web.utils.common_data import GENDER_TYPE_DESC, IMAGE_TYPE_DESC, INDEX_BLOCK_DESC, BOOK_TYPE_DESC

# 性别选项
GENDER_CHOICES = ((GENDER_TYPE_DESC.Male, '男'), (GENDER_TYPE_DESC.Female, '女'),
                  (GENDER_TYPE_DESC.Anonymous, '未知'))

# 图片选项
IMAGE_TYPE = (
    (IMAGE_TYPE_DESC.COVER, '封面'),
    (IMAGE_TYPE_DESC.CHAPER_CONTENT, '章节内容'),
)

# 图片展示选项
BLOCK_DESC_CHOICES = (
    (INDEX_BLOCK_DESC.Carousel, "轮播图"),
    (INDEX_BLOCK_DESC.Photo_Left, "图片在左"),
    (INDEX_BLOCK_DESC.Photo_Top, "图片在上"),
)

# 书本类型选项
BOOK_TYPE_CHOICES = (
    (BOOK_TYPE_DESC.Comic, "漫画"),
    (BOOK_TYPE_DESC.Novel, "小说"),
)


class Author(BaseModel):
    name = models.CharField('作者名', max_length=60, default="anonymous")
    gender = models.CharField('性别',
                              max_length=2,
                              default="A",
                              choices=GENDER_CHOICES)
    mobile_phone = models.CharField("手机号", default="", max_length=20)

    class Meta:
        verbose_name_plural = '作者'
        db_table = 'author'

    def __str__(self):
        return self.name


class Image(BaseModel):
    """图片"""
    img_type = models.CharField('图片类型',
                                null=True,
                                max_length=30,
                                default='',
                                choices=IMAGE_TYPE)
    order = models.IntegerField('排序位置', default=0)
    active = models.BooleanField('生效', default=True)
    name = models.CharField('名称', max_length=255, default='')
    key = models.CharField("图片ID KEY", max_length=50, default="")
    origin_addr = models.CharField('原始地址',
                                   max_length=200,
                                   unique=True,
                                   default="")

    class Meta:
        db_table = 'image'
        verbose_name_plural = '图片'
        ordering = ['order']

    def get_url(self, quality='thumbicon'):
        path = photo_lib.build_photo_url(self.key, quality)
        path = path.replace('\\', '/')
        return path

    def get_path(self, quality='thumbicon'):
        path = photo_lib.build_photo_path(self.key, quality)
        path = path.replace('\\', '/')
        return path

    def __str__(self):
        return self.name


# 书本表
class Book(BaseModel):
    title = models.CharField('书本名称', max_length=60, default='')
    book_type = models.CharField('书本类型',
                                 max_length=30,
                                 default='',
                                 choices=BOOK_TYPE_CHOICES)
    author = models.ForeignKey(Author, on_delete=models.DO_NOTHING)
    cover = models.ManyToManyField(Image, null=True)
    collection_num = models.IntegerField('收藏数量', null=True, default=0)
    click_num = models.IntegerField('点击数量', null=True, default=0)
    desc = models.CharField('描述', max_length=500, default="")
    markup = models.CharField('标签', null=True, max_length=100, default='')
    on_shelf = models.BooleanField('是否上架', default=True)
    is_download = models.BooleanField('是否可以下载', default=False)
    is_finished = models.BooleanField('是否能已完结', default=False)
    origin_addr = models.CharField('原始地址',
                                   max_length=200,
                                   unique=True,
                                   default="")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = '书本'
        db_table = 'book'
        ordering = ['-update_at']
        permissions = (
            ('book_add', '添加书本'),
            ('book_edit', '编辑书本'),
            ('book_detail', '查看书本'),
            ('book_delete', '删除书本'),
        )

    def latest_chapter(self):
        chapter = Chapter.normal.filter(
            book_id=self.id,
            book_type=self.book_type).order_by('-create_at').first()
        return chapter


class Chapter(BaseModel):
    '''章节表'''
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    book_type = models.CharField('书本类型',
                                 max_length=30,
                                 default='',
                                 choices=BOOK_TYPE_CHOICES)
    title = models.CharField('章节标题', null=False, max_length=60, default="")
    number = models.IntegerField('章节编号', default=0)
    order = models.IntegerField('排序位置', default=0)
    active = models.BooleanField('生效', default=False)
    origin_addr = models.CharField('原始地址',
                                   max_length=200,
                                   unique=True,
                                   default="")

    class Meta:
        verbose_name_plural = '章节'
        db_table = 'chapter'
        ordering = ['order', '-update_at']
        permissions = (
            ('chapter_add', '添加章节'),
            ('chapter_edit', '编辑章节'),
            ('chapter_detail', '查看章节'),
            ('chapter_delete', '删除章节'),
        )

    def save_path(self):
        book_path = os.path.join(settings.UPLOAD_SAVE_PATH, self.book_type,
                                 self.book.title)
        chapter_name = '{}_{}.txt'.format(self.order, self.title)
        if not os.path.exists(book_path):
            os.makedirs(book_path, 0o775)
        save_file = os.path.join(book_path, chapter_name)
        return save_file

    def save_content(self, content):
        """保存当前对象章节内容"""
        save_path = self.save_path()
        if self.book_type == BOOK_TYPE_DESC.Novel:
            with open(save_path, 'w', encoding='UTF-8') as f:
                f.write(content)
                # f.flush()
        elif self.book_type == BOOK_TYPE_DESC.Comic:
            cis = [
                ChapterImage(book=self.book,
                             chapter_id=self.id,
                             image=image,
                             order=index)
                for index, image in enumerate(content, 1)
            ]
            ChapterImage.normal.bulk_create(cis)
        self.active = True
        self.save()

    @property
    def content(self):
        """获取当前对象章节内容"""
        if self.book_type == BOOK_TYPE_DESC.Novel:
            content = ''
            with open(self.save_path(), 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        elif self.book_type == BOOK_TYPE_DESC.Comic:
            img_ids = ChapterImage.normal.filter(
                book=self.book, chapter=self.pk).values_list('image')
            img_id_list = [i[0] for i in img_ids]
            imgs = Image.normal.filter(id__in=img_id_list)
            urls = []
            for img in imgs:
                urls.append(img.get_url())
            return urls
        return ''

    def __str__(self):
        return self.title


class ChapterImage(BaseModel):
    '''章节图片中间表'''
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    order = models.IntegerField('排序位置', default=0)
    active = models.BooleanField('生效', default=True)

    class Meta:
        verbose_name_plural = '章节图片中间表'
        db_table = 'chapterimage'


class SubscribeBook(BaseModel):
    user = models.ForeignKey(User, default=1, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True)
    active = models.BooleanField('生效', default=True)
    ready = models.BooleanField('可推送', default=False)
    chapter_num = models.IntegerField('章节每更新次数推送', default=1)
    count = models.IntegerField('推送次数', default=0)
    order = models.IntegerField('排序位置', default=0)

    class Meta:
        verbose_name_plural = '订阅'
        db_table = 'subscribebook'