from django.core.cache import cache


class RunInfo(object):
    def __init__(self, key, total):
        self.key = key
        self.total = total

    def set(self, val: int):
        cache.set(self.key, val)

    def get(self):
        return cache.get(self.key)

    def process(self):
        current = self.get()
        process = round(100 * current / self.total, 2)
        return process


class TaskRunInfo(RunInfo):
    def __init__(self, task_id, total, user_id=None):
        key = '{}_task_{}'.format(task_id, user_id)
        super().__init__(key, total)