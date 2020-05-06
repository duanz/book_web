import re
regular = {}

comic_regular = {
    'manhua.dmzj.com': 'DmzjParser',
    'dmzj.com': 'ComDmzjParser',
    'e-hentai.org': 'EhentaiParser'
}

novel_regular = {
    "biqudao.com": "BiqudaoParser",
    "biqugex.com": "BiqugexParser",
    "biquge.tv": "BiqugexParser",
    "qb5.tw": "TwQb5Parser"
}

regular.update(comic_regular)
regular.update(novel_regular)


def get_parser(url):
    for (k, v) in regular.items():
        if re.search(k, url):
            if k in comic_regular:
                module = __import__('book_web.spiders.comic_parser.' + v,
                                    fromlist=[v])
            elif k in novel_regular:
                module = __import__('book_web.spiders.novel_parser.' + v,
                                    fromlist=[v])

            return getattr(module, v)()
