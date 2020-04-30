from django.contrib.auth.models import User
from django.db import models

from book_web.utils.base_model import BaseModel

GENDER_CHOICES = (('M', '男'), ('F', '女'), ('U', '未知'))


class UserInfo(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES)
    group_id = models.IntegerField(null=False, default=-1)
    inviter_id = models.IntegerField(null=True, default=0)
    markup = models.CharField(null=True, max_length=300, default='')
    phone = models.CharField(null=True, max_length=30, default='')
    avatar_url = models.CharField(null=True, max_length=250, default='')

    class Meta:
        db_table = 'userinfo'
