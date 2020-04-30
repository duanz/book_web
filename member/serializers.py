from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from member.models import UserInfo, GENDER_CHOICES
from book_web.utils.base_logger import logger as logging


class UserSerializer(serializers.ModelSerializer):
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('token', "password", "username", "first_name", "last_name",
                  "email")

        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'token': {
                'read_only': True
            },
        }

    def get_token(self, obj):
        try:
            if self.context.get('request').user.id != obj.id:
                logging.info(
                    'get token illegal, data not belong to current user')
                return ''
            token = Token.objects.get_or_create(user=obj)[0].key
            return token
        except Exception as e:
            logging.error('get token error: {}'.format(e))
            return ''

    def validate_username(self, value):
        print(value)
        method = self.context.get('request').method
        try:
            member = User.objects.get(username__exact=value)
        except User.DoesNotExist:
            member = False

        if member and method in ['POST', 'PUT']:
            raise serializers.ValidationError('该名称已存在.')
        return value

    def validate_password(self, val):
        if len(val) < 6:
            raise serializers.ValidationError('密码至少6个字符')
        return val

    def create(self, validated_data):
        instance = User.objects.create_user(**validated_data)
        return instance

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            instance.set_password(validated_data.get('password'))
            validated_data.pop('password')
        return super().update(instance, validated_data)


class UserLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password')
