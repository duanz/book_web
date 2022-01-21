import os
import subprocess

from django.conf import settings
from rest_framework import serializers
from rest_framework.reverse import reverse

from book.models import Author, Book, Chapter, ChapterImage, Image, SubscribeBook
from book_web.utils.common_data import (
    GENDER_TYPE_DESC,
    IMAGE_TYPE_DESC,
    INDEX_BLOCK_DESC,
    BOOK_TYPE_DESC,
)
from book_web.utils import photo as photo_lib


class AuthorSerializer(serializers.ModelSerializer):
    create_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)

    class Meta:
        model = Author
        fields = "__all__"


class SubscribeBookSerializer(serializers.ModelSerializer):
    create_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)
    update_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)
    book_id = serializers.IntegerField(required=True)
    title = serializers.SerializerMethodField()
    subscribe_id = serializers.SerializerMethodField()

    class Meta:
        model = SubscribeBook
        fields = "__all__"
        extra_kwargs = {
            "user": {"read_only": True},
            "create_at": {"read_only": True},
            "update_at": {"read_only": True},
            "book": {"read_only": True},
            "chapter": {"read_only": True},
            "book_id": {"write_only": True},
        }

    def get_title(self, obj):
        return obj.book.title

    def get_subscribe_id(self, obj):
        return obj.id

    def validated_book_id(self, value):
        if Book.normal.filter(id=value).exists():
            return value
        else:
            raise serializers.ValidationError("订阅的资源不存在")
        if SubscribeBook.normal.filter(
            book_id=value, user_id=self.context["request"].user.id
        ).exists():
            raise serializers.ValidationError("订阅资源已经订阅")

    def validate(self, attrs):
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        validated_data["chapter"] = (
            Chapter.normal.filter(book_id=validated_data["book_id"])
            .order_by("order")
            .first()
        )
        validated_data["book"] = Book.normal.get(id=validated_data["book_id"])
        validated_data["active"] = True
        # 首次创建即可推送
        if validated_data["chapter"]:
            validated_data["ready"] = True

        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        validated_data["user"] = self.context["request"].user
        validated_data["chapter"] = Chapter.normal.filter(
            book_id=validated_data["book_id"]
        ).first()
        validated_data["book"] = Book.normal.get(id=validated_data["book_id"])
        instance = super().update(instance, validated_data)
        return instance


class ImageSerializer(serializers.ModelSerializer):
    create_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)
    url = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = "__all__"

    def get_url(self, obj):
        return obj.get_url(obj.key, self.context.get("quality", "thumb"))

    def get_path(self, obj):
        return obj.get_path(obj.key, self.context.get("quality", "thumb"))


class ImageOnlyUrlSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ("url",)

    def get_url(self, obj: Image):
        return self.context["request"].build_absolute_uri(
            obj.get_path(obj.key, self.context.get("quality", "thumb"))
        )


class ChapterImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ChapterImage
        fields = ("url",)

    def get_url(self, obj):
        return obj.image.get_url(obj.image.key, self.context.get("quality", "thumb"))


class ChapterSerializer(serializers.ModelSerializer):
    update_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)

    class Meta:
        model = Chapter
        fields = (
            "id",
            "book",
            "book_type",
            "title",
            "number",
            "order",
            "update_at",
            "active",
            "origin_addr",
        )


class ChapterDetailSerializer(serializers.ModelSerializer):
    create_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)
    update_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)
    relate_chapter = serializers.SerializerMethodField()
    book_title = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = (
            "id",
            "book",
            "title",
            "number",
            "order",
            "active",
            "create_at",
            "update_at",
            "origin_addr",
            "relate_chapter",
            "content",
            "book_title",
        )

    def get_book_title(self, obj):
        return obj.book.title

    def get_content(self, obj):
        return obj.content

    def get_relate_chapter(self, obj):
        ids = Chapter.normal.filter(
            book=obj.book,
            book_type=obj.book_type,
            order__in=[obj.order - 1, obj.order + 1],
        ).values_list("id")
        id_list = [i[0] for i in ids]
        relate = {"pre_id": 0, "next_id": 0}
        if len(id_list) == 2:
            relate = {"pre_id": id_list[0], "next_id": id_list[1]}
        elif len(id_list) == 1:
            if obj.order == 0:
                relate = {"pre_id": 0, "next_id": id_list[-1]}
            else:
                relate = {"pre_id": id_list[0], "next_id": 0}
        get_url = (
            lambda id: reverse(
                "book_api:chapter-detail", args=[id], request=self.context["request"]
            )
            if id
            else None
        )
        relate["pre"] = get_url(relate["pre_id"])
        relate["next"] = get_url(relate["next_id"])

        return relate


class BookSerializer(serializers.ModelSerializer):
    create_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)
    update_at = serializers.DateTimeField(format="%Y-%m-%d", required=False)
    author = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    subscribe_id = serializers.SerializerMethodField(required=False)

    class Meta:
        model = Book
        fields = (
            "id",
            "create_at",
            "status",
            "update_at",
            "title",
            "book_type",
            "author",
            "cover",
            "collection_num",
            "click_num",
            "desc",
            "markup",
            "on_shelf",
            "is_finished",
            "download_url",
            "is_download",
            "subscribe_id",
            "cover",
        )
        read_only_fields = (
            "cover",
            "download_url",
            "is_download",
            "cover",
            "subscribe_id",
        )

    def get_author(self, obj):
        return str(obj.author)

    def get_cover(self, obj):
        context = self.context
        context["quality"] = context["quality"] if context.get("quality") else "title"
        img_obj = obj.cover.last()
        key = img_obj.key if img_obj else None
        url = self.context["request"].build_absolute_uri(
            Image.get_path(key, self.context.get("quality", "thumb"))
        )
        return url

    def get_subscribe_id(self, obj):
        if not self.context["request"].user.id:
            return 0
        sb = SubscribeBook.normal.filter(
            book_id=obj.id, user_id=self.context["request"].user.id
        ).first()
        if sb:
            return sb.id
        return 0

    def get_download_url(self, obj):
        path = ""
        if obj.is_download:
            path = settings.APP_HOST + os.path.join(
                settings.MEDIA_ROOT, obj.title + ".txt"
            )
        return path


class BookDetailSerializer(BookSerializer):
    chapter = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            "id",
            "create_at",
            "status",
            "update_at",
            "title",
            "collection_num",
            "click_num",
            "desc",
            "markup",
            "on_shelf",
            "is_finished",
            "author",
            "chapter",
            "cover",
        )

        read_only_fields = ("chapter", "cover", "is_subscribe")

    def get_chapter(self, obj):
        chapters = Chapter.normal.filter(book_id=obj.id)
        return ChapterSerializer(chapters, many=True).data
