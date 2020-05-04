import re
import os
import requests


def decode_packed_codes(code):
    def encode_base_n(num, n, table=None):
        FULL_TABLE = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if not table:
            table = FULL_TABLE[:n]

        if n > len(table):
            raise ValueError('base %d exceeds table length %d' %
                             (n, len(table)))

        if num == 0:
            return table[0]

        ret = ''
        while num:
            ret = table[num % n] + ret
            num = num // n
        return ret

    pattern = r"}\('(.+)',(\d+),(\d+),'([^']+)'\.split\('\|'\)"
    mobj = re.search(pattern, code)
    obfucasted_code, base, count, symbols = mobj.groups()
    base = int(base)
    count = int(count)
    symbols = symbols.split('|')
    symbol_table = {}

    while count:
        count -= 1
        base_n_count = encode_base_n(count, base)
        symbol_table[base_n_count] = symbols[count] or base_n_count

    return re.sub(r'\b(\w+)\b', lambda mobj: symbol_table[mobj.group(0)],
                  obfucasted_code)


def mkdir(path):
    path_ = path.split('/')

    for i in range(0, len(path_)):
        p = '/'.join(path_[0:i + 1])
        if p and not os.path.exists(p):
            os.mkdir(p)


def get_proxy_ip():
    """获取代理ip"""

    url = "http://127.0.0.1:5010/get"
    res = []
    try:
        for i in range(10):
            res.append(requests.get(url, timeout=3).json())
    except:
        return []
    if not res:
        return

    ips = []
    for info in res:
        ips.append('http://{}'.format(info['proxy']))

    ok_ips = available_ip(set(ips))
    ok_ips = set((ips))
    return list(ok_ips)


def available_ip(ip_list):
    headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 \
        (KHTML, like Gecko) Chrome/65.0.3325.146 Safari/537.36',
    }
    sesseion = requests.session()
    ips = []
    for ip in ip_list:
        try:
            response = sesseion.get('https://www.baidu.com',
                                    headers=headers,
                                    proxies={'http': ip},
                                    verify=False,
                                    timeout=3)
            if response.status_code == 200:
                ips.append(ip)
        except TimeoutError:
            continue
    return ips
