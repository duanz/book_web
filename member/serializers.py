from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from book_web.utils.base_logger import logger as logging
from book_web.utils import spider_utils as utils
from member.models import ActiveCode


class UserSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("token", "password", "username", "first_name", "last_name", "email")

        extra_kwargs = {
            "password": {"write_only": True},
            "token": {"read_only": True},
        }

    def get_token(self, obj):
        try:
            if self.context.get("request").user.id != obj.id:
                logging.info("get token illegal, data not belong to current user")
                return ""
            token = Token.objects.get_or_create(user=obj)[0].key
            return token
        except Exception as e:
            logging.error("get token error: {}".format(e))
            return ""

    def validate_username(self, value):
        method = self.context.get("request").method
        try:
            member = User.objects.get(username__exact=value)
        except User.DoesNotExist:
            member = False

        if member and method in ["POST", "PUT"]:
            raise serializers.ValidationError("该名称已存在.")
        return value

    def validate_email(self, value):
        if value and "@kindle" not in value:
            raise serializers.ValidationError("该邮箱不是kindle设备.")
        method = self.context.get("request").method
        try:
            member = User.objects.get(email__exact=value)
        except User.DoesNotExist:
            member = False

        if member and method in ["POST", "PUT"]:
            raise serializers.ValidationError("该邮箱已存在.")
        return value

    def validate_password(self, val):
        if len(val) < 6:
            raise serializers.ValidationError("密码至少6个字符")
        return val

    def create(self, validated_data):
        instance = User.objects.create_user(**validated_data)
        return instance

    def update(self, instance, validated_data):
        if "password" in validated_data:
            instance.set_password(validated_data.get("password"))
            validated_data.pop("password")
        return super().update(instance, validated_data)


class UserLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "password")


# user = models.OneToOneField(User, on_delete=models.CASCADE)
# inviter_id = models.IntegerField(null=True, default=0)
# period = models.IntegerField("生效天数", null=True, default=30)
# markup = models.CharField(null=True, max_length=300, default='')
# code = models.CharField('激活码', null=True, max_length=60, default='')
# used = models.BooleanField('是否已经使用', default=False)
# worked = models.BooleanField('是否有效', default=False)
# active_at = models.DateTimeField('激活时间', default=timezone.now)


class ActiveCodeSerializer(serializers.ModelSerializer):
    create_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)
    update_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)
    active_at = serializers.DateTimeField(format="%Y-%m-%d %H:%I:%S", required=False)

    class Meta:
        model = ActiveCode
        fields = "__all__"

        extra_kwargs = {
            "user": {"read_only": True},
            "create_at": {"read_only": True},
            "update_at": {"read_only": True},
            "active_at": {"read_only": True},
        }

    def validate_user(self, val):
        user = self.context["request"].user
        if not user:
            raise serializers.ValidationError("请先登录，再进行激活！")
        return user

    def validate_create_user(self, val):
        create_user = self.context["request"].user
        if not create_user.is_staff:
            raise serializers.ValidationError("该激活码创建不合法，不要做无谓的尝试了：）")
        return create_user

    def validate_code(self, val):
        code = utils.get_key()
        while ActiveCode.normal.filter(code=code).count():
            code = utils.get_key()
        return code

    def create(self, validated_data):
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        if "code" in validated_data:
            validated_data.pop("code")
        instance = super().update(instance, validated_data)
        return instance
