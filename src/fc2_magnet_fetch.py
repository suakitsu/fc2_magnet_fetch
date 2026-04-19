# -*- coding:utf-8 -*-
"""
FC2番号&磁力批量获取
"""
import requests, os, sys, time, re, threading
from configparser import RawConfigParser
from traceback import format_exc

VERSION = 'v2.0.0'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
proxy = ''
proxie = {}
download_path = ''
max_dl = 2
max_retry = 3
session = None
idlist = []
mu = threading.Lock()
stop_event = threading.Event()

# FC2 标签列表 (id -> 中文名)
GENRES = {
    30: '素人',
    31: '美丽女人',
    32: 'OL',
    33: '恋物癖/变态',
    34: '巨乳/美乳',
    35: '自拍',
    36: '自慰',
    37: '野外/露出',
    38: 'Cosplay/同人',
    39: '乱交/3P',
    40: '男性同性',
    41: '西方金发/白人',
    42: '动漫/卡通',
    43: '其他',
    44: 'SM',
    45: 'BL',
}

def _config_path():
    return os.path.join(BASE_DIR, 'config.ini')

def _download_path():
    return os.path.join(BASE_DIR, 'Downloads')


def read_config():
    global proxy, proxie, download_path, max_dl, max_retry, session

    fcu = ''
    phpsessid = ''
    cookies_str = ''
    cpath = _config_path()

    if os.path.exists(cpath):
        cfg = RawConfigParser()
        try:
            cfg.read(cpath, encoding='UTF-8-SIG')
            proxy = cfg.get("下载设置", "Proxy")
            dp = cfg.get("下载设置", "Download_Path")
            download_path = dp if os.path.isabs(dp) else os.path.join(BASE_DIR, dp.replace('./', '').rstrip('/')) + os.sep
            max_dl = int(cfg.get("下载设置", "Max_dl"))
            max_retry = int(cfg.get("下载设置", "Max_retry"))
            try: cookies_str = cfg.get("下载设置", "Cookies")
            except: cookies_str = ''
            try: fcu = cfg.get("下载设置", "fcu")
            except: fcu = ''
            try: phpsessid = cfg.get("下载设置", "PHPSESSID")
            except: phpsessid = ''
        except:
            print(format_exc())
            print('config.ini 读不了，看看格式对不对')
            os.system('pause>nul')
            sys.exit()
    else:
        _gen_config()
        print('没有config.ini，已生成模板，填好了再跑')
        os.system('pause>nul')
        sys.exit()

    if not phpsessid or not fcu:
        print('Cookie没填！FC2不登录搜不了东西的')
        print('去config.ini填PHPSESSID和fcu，不知道怎么拿就选菜单5看')
        os.system('pause>nul')
        sys.exit()

    if not os.path.exists(download_path):
        os.makedirs(download_path)

    if proxy not in ('否', 'no', ''):
        proxie = {'http': proxy, 'https': proxy}

    session = requests.Session()
    session.mount('http://', requests.adapters.HTTPAdapter(max_retries=max_retry))
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=max_retry))

    cookies = {
        'CONTENTS_FC2_PHPSESSID': phpsessid,
        'fcu': fcu,
        'fcus': fcu,
        'contents_mode': 'digital',
        'contents_func_mode': 'buy',
        'language': 'cn',
        'GDPRCHECK': 'true',
        'wei6H': '1',
    }
    if cookies_str:
        for item in cookies_str.split('; '):
            if '=' in item:
                key, val = item.split('=', 1)
                key = key.strip()
                if key and key not in ['fcu', 'fcus', 'PHPSESSID', 'CONTENTS_FC2_PHPSESSID']:
                    cookies[key] = val

    for k, v in cookies.items():
        session.cookies.set(k, v, domain='.fc2.com')

    p = "开了 " + proxy if proxie else "没开"
    print(f'配置加载好了 (代理{p})')
    print(f'Cookie: PHPSESSID={phpsessid[:8]}... fcu={fcu[:8]}...')


def _gen_config():
    s = """[下载设置]
Proxy = http://localhost:10808
Download_Path = ./Downloads/
Max_dl = 2
Max_retry = 3
Cookies = 
fcu = 
PHPSESSID = 
"""
    with open(_config_path(), 'w', encoding='UTF-8-SIG') as f:
        f.write(s)
    print(f'生成了config.ini 在 {_config_path()}')


def requests_web(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://adult.contents.fc2.com/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
    }
    try:
        if proxie:
            r = session.get(url, headers=headers, proxies=proxie, timeout=15)
        else:
            r = session.get(url, headers=headers, timeout=15)
        r.encoding = 'utf-8'
    except Exception as e:
        print(f'网络炸了: {e}')
        return None

    if r.status_code == 302 or 'login.php' in r.url:
        print('Cookie过期了，重新登录FC2再更新config.ini')
        return None
    if r.status_code != 200:
        print('连接错误: ' + str(r.status_code))
        return None
    return r.text


def fc2_get_next_page(txt):
    p = re.compile('<span class="items" aria-selected="true">.*?</span>.*?<a data-pjx="pjx-container" data-link-name="pager".*?href=".*?&page=([0-9]*)" class="items">.*?<', re.S)
    keys = re.findall(p, txt)
    return int(keys[0]) if keys else 0


def parse_fc2id(txt):
    patterns = [
        re.compile(r'<div class="c-cntCard-110-f"><div class="c-cntCard-110-f_thumb"><a href="/article/(\d+)/"', re.S),
        re.compile(r'href="/article/(\d+)/"', re.S),
    ]
    seen = set()
    for p in patterns:
        for item in p.findall(txt):
            if item not in seen:
                seen.add(item)
                yield item


def parse_magnet(html):
    p = re.compile(r'<a href="magnet:\?xt=(.*?)&amp;dn=', re.S)
    urls = p.findall(html)
    return 'magnet:?xt=' + urls[0] if urls else None


def write_to_file(filename, txt):
    with open(download_path + filename, 'a', encoding='UTF-8') as f:
        f.write(txt + '\n')


def clean_list(filename):
    fp = download_path + filename
    print('清空 ===> ' + fp)
    with open(fp, 'w', encoding='UTF-8') as f:
        f.truncate(0)


def read_list(file):
    fp = download_path + file
    if os.path.exists(fp):
        with open(fp, encoding='utf-8') as f:
            return f.readlines()
    print('没找到list.txt，先去获取番号')
    return None


def get_fc2id(url, max_count=0):
    clean_list('list.txt')
    collected = []
    page = 1
    next_page = 1

    while next_page > 0:
        if max_count > 0 and len(collected) >= max_count:
            break
        print(f'第{page}页...')
        html = requests_web(url)
        if html is None:
            print('页面拿不到，停了')
            break

        for num in parse_fc2id(html):
            if max_count > 0 and len(collected) >= max_count:
                break
            if num not in collected:
                collected.append(num)
                write_to_file('list.txt', 'FC2 ' + str(num))
                print(f'  [{len(collected)}] FC2-{num}')

        next_page = fc2_get_next_page(html)
        if next_page > 0:
            if '&' in url and 'page=' in url:
                url = re.sub(r'page=\d+', f'page={next_page}', url)
            else:
                url = url + '&page=' + str(next_page)
            page += 1
        else:
            break

    print(f'\n搞定，{len(collected)}个番号，在{download_path}list.txt')


def get_magnet(start, stop):
    for i in range(start, stop):
        if stop_event.is_set():
            return
        try:
            url = 'https://sukebei.nyaa.si/?f=0&c=0_0&q=' + idlist[i].strip() + '&s=downloads&o=desc'
            html = requests_web(url)
            if html is not None:
                magnet = parse_magnet(html)
                if magnet is not None:
                    mu.acquire()
                    write_to_file('magnet.txt', str(magnet))
                    print(f'  ok [{i+1}/{stop}] ====> {idlist[i].strip()}')
                    mu.release()
                else:
                    mu.acquire()
                    write_to_file('no_magnet.txt', idlist[i].strip())
                    print(f'  没找到 [{i+1}/{stop}] ====> {idlist[i].strip()}')
                    mu.release()
            else:
                mu.acquire()
                write_to_file('error.txt', idlist[i].strip() + ' -- 连接失败')
                mu.release()
            time.sleep(1)
        except:
            pass


def creta_thread():
    stop_event.clear()
    lmax = len(idlist)
    remaider = lmax % int(max_dl)
    number = int(lmax / int(max_dl))
    offset = 0
    threads = []

    for i in range(int(max_dl)):
        if remaider > 0:
            t = threading.Thread(target=get_magnet, args=(i * number + offset, (i + 1) * number + offset + 1))
            remaider -= 1
            offset += 1
        else:
            t = threading.Thread(target=get_magnet, args=(i * number + offset, (i + 1) * number + offset))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.1)

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('\n\nCtrl+C 收到，停了')
        stop_event.set()
        time.sleep(1)
        print('已停，拿到的数据都存着呢')


def input_url():
    print('\nURL格式:')
    print('  搜索: https://adult.contents.fc2.com/search/?genre[2]=38')
    print('  用户: https://adult.contents.fc2.com/users/xxx/articles?sort=date&order=desc')
    while True:
        url = input("\n输入FC2页面URL: ").strip()
        if 'adult.contents.fc2.com' in url:
            return url
        print('URL不对，要fc2内容站的')


def pick_genres():
    """选标签，返回拼好的搜索URL"""
    items = sorted(GENRES.items(), key=lambda x: x[0])
    print('\n  FC2 标签列表')
    print('  ' + '-' * 30)
    for gid, name in items:
        print(f'  [{gid}] {name}')
    print('  ' + '-' * 30)
    print('  输入编号，多个用空格或逗号隔开')
    print('  例: 38 42  (回车=全不选)')
    
    raw = input("\n选标签: ").strip()
    if not raw:
        return None
    
    # 解析用户输入的编号
    selected = []
    for part in re.split(r'[\s,，]+', raw):
        part = part.strip()
        if part.isdigit():
            g_id = int(part)
            if g_id in GENRES and g_id not in selected:
                selected.append(g_id)

    if not selected:
        print('没选到有效的标签')
        return None

    # 拼URL
    qs_parts = [f'genre[{i+1}]={g}' for i, g in enumerate(selected)]
    url = 'https://adult.contents.fc2.com/search/?' + '&'.join(qs_parts)
    names = ', '.join(GENRES[g] for g in selected)
    print(f'\n已选: {names}')
    print(f'URL: {url}\n')
    return url


def set_menu():
    global idlist
    while True:
        print(f"""
  FC2 Magnet Tool {VERSION}
  ══════════════════════════
   1: 选标签获取（指定数量）
   2: 选标签获取（全部）
   3: 手动输入URL获取
   4: 获取磁力（Ctrl+C可中断）
   5: 看看list.txt
   6: 更新Cookies
   q: 退出
  ══════════════════════════""")
        cmd = input("选: ").strip()

        if cmd == '1':
            url = pick_genres()
            if url:
                c = input("要几个（0=全要）: ").strip()
                c = int(c) if c.isdigit() else 0
                get_fc2id(url, max_count=c)

        elif cmd == '2':
            url = pick_genres()
            if url:
                get_fc2id(url)

        elif cmd == '3':
            get_fc2id(input_url())

        elif cmd == '4':
            idlist = read_list('list.txt')
            if idlist:
                clean_list('magnet.txt')
                clean_list('no_magnet.txt')
                clean_list('error.txt')
                print(f'\n开始找{len(idlist)}个番号的磁力...')
                print('按Ctrl+C能停，已拿到的不会丢\n')
                creta_thread()
                print(f'\n磁力搞定，在{download_path}')
            else:
                print('没番号列表，先去获取')

        elif cmd == '5':
            fp = download_path + 'list.txt'
            if os.path.exists(fp):
                with open(fp, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                print(f'\n--- list.txt ({len(lines)}条) ---')
                for line in lines[:20]:
                    print('  ' + line.strip())
                if len(lines) > 20:
                    print(f'  ... 还有{len(lines)-20}条')
            else:
                print('list.txt不存在')

        elif cmd == '6':
            print('\n怎么拿Cookie:')
            print('  1. 浏览器登录 https://adult.contents.fc2.com/')
            print('  2. F12 → Application → Cookies')
            print('  3. 复制 CONTENTS_FC2_PHPSESSID 和 fcu 的值')
            phpsessid = input('\nPHPSESSID: ').strip()
            fcu_val = input('fcu: ').strip()
            if phpsessid:
                session.cookies.set('CONTENTS_FC2_PHPSESSID', phpsessid, domain='.fc2.com')
                print('PHPSESSID 更新了（只管这次，要长久改config.ini）')
            if fcu_val:
                session.cookies.set('fcu', fcu_val, domain='.fc2.com')
                session.cookies.set('fcus', fcu_val, domain='.fc2.com')
                print('fcu 更新了（只管这次，要长久改config.ini）')
            if not phpsessid and not fcu_val:
                print('啥都没输啊')

        elif cmd == 'q':
            sys.exit(0)

        else:
            print('选错了重来')


if __name__ == '__main__':
    print(f'\n  FC2 Magnet Tool {VERSION}')
    print('  ═══════════════════════')
    read_config()
    idlist = read_list("list.txt") or []
    set_menu()
