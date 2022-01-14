import re
import os
import requests
import string
import random
from tqdm import tqdm


def get_key(key="", n=12):
    # 随机码最少4位
    if n < 4:
        raise AttributeError
    word = string.digits + string.ascii_letters
    for i in range(1, n + 1):
        key += random.choice(word)  # 获取随机字符或数字
        if i % 4 == 0 and i != n:  # 每隔4个字符增加'-'
            key += "-"
    return key


def decode_packed_codes(code):
    def encode_base_n(num, n, table=None):
        FULL_TABLE = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if not table:
            table = FULL_TABLE[:n]

        if n > len(table):
            raise ValueError("base %d exceeds table length %d" % (n, len(table)))

        if num == 0:
            return table[0]

        ret = ""
        while num:
            ret = table[num % n] + ret
            num = num // n
        return ret

    pattern = r"}\('(.+)',(\d+),(\d+),'([^']+)'\.split\('\|'\)"
    mobj = re.search(pattern, code)
    obfucasted_code, base, count, symbols = mobj.groups()
    base = int(base)
    count = int(count)
    symbols = symbols.split("|")
    symbol_table = {}

    while count:
        count -= 1
        base_n_count = encode_base_n(count, base)
        symbol_table[base_n_count] = symbols[count] or base_n_count

    return re.sub(
        r"\b(\w+)\b", lambda mobj: symbol_table[mobj.group(0)], obfucasted_code
    )


def validateFilename(title):
    rstr = r"[\/\\\:\*\?\"\<\>\|]"  # '/ \ : * ? " < > |'
    new_title = re.sub(rstr, "", title)  # 去掉非法字符
    return new_title


def mkdir(path):
    path_ = path.split("/")

    for i in range(0, len(path_)):
        p = "/".join(path_[0 : i + 1])
        if p and not os.path.exists(p):
            os.mkdir(p)


def get_proxy_ip(count=100):
    """获取代理ip"""

    # url = "http://127.0.0.1:5010/get"
    url = f"http://ip.memories1999.com/api.php?dh=1265918268935079196&sl={count}"
    res = requests.get(url, timeout=3).text
    res = res.splitlines()
    # print(res)
    # res = []
    # try:
    #     for i in range(50):
    #         res.append(requests.get(url, timeout=3).json())
    # except:
    #     return []
    # if not res:
    #     return

    ips = []
    for info in res:
        ips.append("http://{}".format(info))

    ips = available_ip(set(ips))
    print(f"可用proxy ip有{len(ips)}")
    return ips


def available_ip(ip_list):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36",
        "Connection": "close",
    }

    # sesseion = requests.session()
    ips = []
    for ip in tqdm(ip_list, desc="验证IP"):
        try:
            response = requests.get(
                "http://cn.bing.com/",
                proxies={"http": ip},
                verify=False,
                timeout=3,
            )
            if response.status_code == 200:
                ips.append(ip)
        except Exception as e:
            # print(f"handle proxy ip cerify: {e}")
            continue
    return ips
