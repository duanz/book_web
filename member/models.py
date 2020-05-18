from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
import django.utils.timezone as timezone

from book_web.utils.base_model import BaseModel
from book_web.utils.common_data import ACTIVECODE_TYPE_DESC
from book_web.utils.spider_utils import get_key

ACTIVECODE_TYPE_CHOICES = (
    (ACTIVECODE_TYPE_DESC.Time, '时间'),
    (ACTIVECODE_TYPE_DESC.Count, '次数'),
)


class ActiveCode(BaseModel):
    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    inviter_id = models.IntegerField(null=True, default=0)
    period = models.IntegerField("生效天数", null=True, default=0)
    subscribe_count = models.IntegerField("订阅次数", null=True, default=0)
    markup = models.CharField("备注", null=True, max_length=300, default='')
    code = models.CharField('激活码',
                            null=True,
                            max_length=60,
                            default=get_key,
                            unique=True)
    used = models.BooleanField('是否已经使用', default=False)
    worked = models.BooleanField('是否有效', default=False)
    active_at = models.DateTimeField('激活时间', default=timezone.now)
    use_type = models.CharField('使用类型',
                                null=True,
                                max_length=10,
                                default=ACTIVECODE_TYPE_DESC.Time,
                                choices=ACTIVECODE_TYPE_CHOICES)

    class Meta:
        db_table = "active_code"
        verbose_name_plural = '激活码'
        ordering = ['create_at', 'period']

    def clean(self):
        if self.use_type == ACTIVECODE_TYPE_DESC.Time and self.period < 1:
            raise ValidationError({'period': '生效天数不少于1天'})

        if self.use_type == ACTIVECODE_TYPE_DESC.Time and self.subscribe_count > 0:
            raise ValidationError({'subscribe_count': '当使用周期是时间时，不可设置订阅次数'})

        if self.use_type == ACTIVECODE_TYPE_DESC.Count and self.period > 0:
            raise ValidationError({'period': '当使用周期是订阅次数时，不可设置生效天数'})

        if self.use_type == ACTIVECODE_TYPE_DESC.Count and self.subscribe_count < 1:
            raise ValidationError({'subscribe_count': '订阅次数不少于1次'})

        while ActiveCode.normal.filter(code=self.code).count:
            self.code = get_key()