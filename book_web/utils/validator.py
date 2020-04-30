from task.models import Task, TASK_STATUS_DESC, TASK_TYPE_DESC
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


def check_url(data):
    valid_url = URLValidator()
    try:
        valid_url(data)
        return True
    except ValidationError:
        return False
