# 性别种类
class GENDER_TYPE_DESC:
    Male = "M"
    Female = "F"
    Anonymous = "A"


# 激活种类
class ACTIVECODE_TYPE_DESC:
    Time = "T"
    Count = "C"


# 图片种类
class IMAGE_TYPE_DESC:
    COVER = 'COVER'
    CHAPER_CONTENT = 'CONTENT'


# 首页描述
class INDEX_BLOCK_DESC:
    Carousel = "CA"
    Photo_Left = "PL"
    Photo_Top = "PT"


# 书本种类描述
class BOOK_TYPE_DESC:
    Comic = "COMIC"
    Novel = "NOVEL"


class TASK_TYPE_DESC:
    NOVEL_INSERT = "NOVEL_INSERT"
    NOVEL_UPDATE = "NOVEL_UPDATE"
    NOVEL_CHAPTER_UPDATE = "NOVEL_CHAPTER_UPDATE"
    COMIC_INSERT = "COMIC_INSERT"
    COMIC_UPDATE = "COMIC_UPDATE"
    COMIC_CHAPTER_UPDATE = "COMIC_CHAPTER_UPDATE"
    NOVEL_MAKE_BOOK = "NOVEL_MAKE_BOOK"
    COMIC_MAKE_BOOK = "COMIC_MAKE_BOOK"
    SEND_TO_KINDLE = "SEND_TO_KINDLE"


class TASK_STATUS_DESC:
    WAIT = "WAIT"
    RUNNING = "RUNNING"
    FINISH = "FINISH"
    FAILD = "FAILD"
