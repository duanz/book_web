import os

os.environ['APP_HOST'] = 'http://ikaka.club:5000'
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = '123456'
os.environ['DB_NAME'] = 'book_web'
os.environ['MYSQL_HOST'] = '127.0.0.1'
os.environ['UPLOAD_SAVE_PATH'] = 'F:/book_web/static/book_web_upload'
os.environ['REDIS'] = 'redis://127.0.0.1:6379/0'

# email 网易163邮箱为例
os.environ["EMAIL_HOST"] = "smtp.163.com"
os.environ["EMAIL_PORT"] = "25"
os.environ["EMAIL_HOST_USER"] = "your@163.com"
os.environ["EMAIL_HOST_PASSWORD"] = "*********"
os.environ["EMAIL_FROM_EMAIL"] = "book_web<your@163.com>"
os.environ["EMAIL_TO_EMAIL"] = "your@kindle.cn, my@kindle.cn"