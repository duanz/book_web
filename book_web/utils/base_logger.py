import logging
import os
from traceback import print_exc

from django.conf import settings


class MyLogger(object):
    def __init__(self, name=__name__):
        # 创建一个logger
        self.logger = logging.getLogger("duan")
        self.logger.setLevel(logging.DEBUG)

        # 创建handler,写入日志
        filename = os.path.join(settings.MEDIA_ROOT, name + ".log")
        fh = logging.FileHandler(filename, encoding="UTF-8")
        fh.setLevel(logging.DEBUG)

        # 创建handler，输出日志到控制台
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # 定义handler的输出格式
        # formatter = logging.Formatter(
        #     '%(asctime)s - %(name)s - %(levelname)s >>> %(message)s')
        formatter = logging.Formatter(
            "%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s"
        )

        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # 给logger添加handler
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def info(self, msg):
        self.logger.info(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def error(self, msg):
        # self.logger.error(msg)
        self.logger.error(print_exc())


logger = MyLogger()
