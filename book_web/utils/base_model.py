from django.db import models
import django.utils.timezone as timezone


class NormalQuerySet(models.QuerySet):
    def delete(self):
        return self.update(status='deleted')

    def hard_delete(self):
        return super().delete()

    def update(self, **kwargs):
        return super().update(update_at=timezone.now(), **kwargs)


class NormalObjectsManager(models.Manager):
    def get_queryset(self):
        return NormalQuerySet(self.model, self._db).filter(status='normal')


class BaseModel(models.Model):
    normal = NormalObjectsManager()
    objects = models.Manager()
    status = models.CharField(max_length=10, default='normal')
    create_at = models.DateTimeField(default=timezone.now)
    update_at = models.DateTimeField(default=timezone.now)

    def save(self, **kwargs):
        self.update_at = timezone.now()
        return super().save(**kwargs)

    def delete(self, **kwargs):
        self.status = 'deleted'
        return self.save()

    def hard_delete(self, **kwargs):
        return super().delete(**kwargs)

    class Meta:
        abstract = True
