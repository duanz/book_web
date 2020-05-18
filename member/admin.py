from django.contrib import admin
from member.models import ActiveCode


# Register your models here.
@admin.register(ActiveCode)
class ActiveCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'use_type', 'user', 'code', 'used', 'worked',
                    'period', 'active_at', 'subscribe_count')
