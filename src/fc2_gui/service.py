from __future__ import annotations

import queue
import re
import threading
import time
from pathlib import Path
from typing import Callable

import requests

from .config import AppConfig
from .constants import GENRES


LogFn = Callable[[str], None]


class FC2Service:
    def __init__(self, config: AppConfig, log: LogFn):
        self.config = config
        self.log = log
        self.session = requests.Session()
        self.session.mount("http://", requests.adapters.HTTPAdapter(max_retries=config.max_retry))
        self.session.mount("https://", requests.adapters.HTTPAdapter(max_retries=config.max_retry))
        self._lock = threading.Lock()
        self._apply_cookies(config.fcu, config.phpsessid, config.cookies)

    def update_runtime_cookies(self, fcu: str, phpsessid: str) -> None:
        self._apply_cookies(fcu, phpsessid, self.config.cookies)
        self.config.fcu = fcu
        self.config.phpsessid = phpsessid

    def _apply_cookies(self, fcu: str, phpsessid: str, cookies_str: str) -> None:
        cookies = {
            "CONTENTS_FC2_PHPSESSID": phpsessid,
            "fcu": fcu,
            "fcus": fcu,
            "contents_mode": "digital",
            "contents_func_mode": "buy",
            "language": "cn",
            "GDPRCHECK": "true",
            "wei6H": "1",
        }
        if cookies_str:
            for item in cookies_str.split("; "):
                if "=" not in item:
                    continue
                key, val = item.split("=", 1)
                key = key.strip()
                if key and key not in ("fcu", "fcus", "PHPSESSID", "CONTENTS_FC2_PHPSESSID"):
                    cookies[key] = val
        for key, val in cookies.items():
            self.session.cookies.set(key, val, domain=".fc2.com")

    def has_required_cookie(self) -> bool:
        return bool(self.config.fcu and self.config.phpsessid)

    def _request_text(self, url: str, require_fc2_auth: bool = False) -> str | None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if "fc2.com" in url:
            headers["Referer"] = "https://adult.contents.fc2.com/"

        try:
            kwargs = {"headers": headers, "timeout": (5, 10)}
            if self.config.proxies:
                kwargs["proxies"] = self.config.proxies
            resp = self.session.get(url, **kwargs)
            resp.encoding = "utf-8"
        except Exception as exc:
            self.log(f"网络请求失败: {exc}")
            return None

        if require_fc2_auth and (resp.status_code == 302 or "login.php" in resp.url):
            self.log("Cookie 可能已过期，请更新后重试。")
            return None
        if resp.status_code != 200:
            self.log(f"HTTP 状态异常: {resp.status_code}")
            return None
        return resp.text

    @staticmethod
    def build_search_url(genre_ids: list[int]) -> str:
        qs = [f"genre[{idx + 1}]={gid}" for idx, gid in enumerate(genre_ids)]
        return "https://adult.contents.fc2.com/search/?" + "&".join(qs)

    @staticmethod
    def genre_name(genre_id: int) -> str:
        return GENRES.get(genre_id, str(genre_id))

    @staticmethod
    def parse_ids(html: str):
        patterns = [
            re.compile(r'<div class="c-cntCard-110-f"><div class="c-cntCard-110-f_thumb"><a href="/article/(\d+)/"', re.S),
            re.compile(r'href="/article/(\d+)/"', re.S),
        ]
        seen = set()
        for pattern in patterns:
            for item in pattern.findall(html):
                if item not in seen:
                    seen.add(item)
                    yield item

    @staticmethod
    def parse_next_page(html: str) -> int:
        pattern = re.compile(
            r'<span class="items" aria-selected="true">.*?</span>.*?<a data-pjx="pjx-container" '
            r'data-link-name="pager".*?href=".*?&page=([0-9]*)" class="items">.*?<',
            re.S,
        )
        found = pattern.findall(html)
        return int(found[0]) if found else 0

    @staticmethod
    def parse_magnet(html: str) -> str | None:
        pattern = re.compile(r'<a href="magnet:\?xt=(.*?)&amp;dn=', re.S)
        links = pattern.findall(html)
        return "magnet:?xt=" + links[0] if links else None

    def _file(self, name: str) -> Path:
        return self.config.download_path / name

    def clear_file(self, name: str) -> None:
        self._file(name).write_text("", encoding="utf-8")

    def append_line(self, name: str, line: str) -> None:
        with self._file(name).open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def read_lines(self, name: str) -> list[str]:
        fp = self._file(name)
        if not fp.exists():
            return []
        return [line.rstrip("\n") for line in fp.read_text(encoding="utf-8").splitlines()]

    def fetch_ids(self, url: str, max_count: int = 0, stop_event: threading.Event | None = None) -> int:
        self.clear_file("list.txt")
        page = 1
        next_page = 1
        collected: list[str] = []
        limit_text = "全部" if max_count <= 0 else str(max_count)
        self.log(f"采集上限: {limit_text}")

        while next_page > 0:
            if stop_event and stop_event.is_set():
                self.log("已收到停止信号，终止采集。")
                break
            if max_count > 0 and len(collected) >= max_count:
                break

            self.log(f"采集第 {page} 页...")
            html = self._request_text(url, require_fc2_auth=True)
            if html is None:
                break

            for num in self.parse_ids(html):
                if stop_event and stop_event.is_set():
                    break
                if max_count > 0 and len(collected) >= max_count:
                    break
                if num not in collected:
                    collected.append(num)
                    self.append_line("list.txt", f"FC2 {num}")
                    self.log(f"  + FC2-{num} ({len(collected)})")
                    if max_count > 0 and len(collected) >= max_count:
                        self.log(f"已达到采集上限 {max_count}，停止翻页。")
                        self.log(f"采集完成，共 {len(collected)} 条，写入 list.txt")
                        return len(collected)

            next_page = self.parse_next_page(html)
            if next_page <= 0:
                break

            if "&" in url and "page=" in url:
                url = re.sub(r"page=\d+", f"page={next_page}", url)
            else:
                url = url + f"&page={next_page}"
            page += 1

        self.log(f"采集完成，共 {len(collected)} 条，写入 list.txt")
        return len(collected)

    def fetch_magnets(self, stop_event: threading.Event | None = None) -> dict[str, int]:
        ids = [line.strip() for line in self.read_lines("list.txt") if line.strip()]
        if not ids:
            self.log("list.txt 为空，请先采集编号。")
            return {"ok": 0, "no_magnet": 0, "error": 0}

        for name in ("magnet.txt", "no_magnet.txt", "error.txt"):
            self.clear_file(name)

        self.log(f"开始检索，共 {len(ids)} 条，线程数={self.config.max_dl}")
        q: queue.Queue[tuple[int, str]] = queue.Queue()
        for idx, item in enumerate(ids):
            q.put((idx, item))

        stats = {"ok": 0, "no_magnet": 0, "error": 0}

        def worker():
            while True:
                if stop_event and stop_event.is_set():
                    return
                try:
                    idx, keyword = q.get_nowait()
                except queue.Empty:
                    return

                try:
                    url = f"https://sukebei.nyaa.si/?f=0&c=0_0&q={keyword}&s=downloads&o=desc"
                    html = self._request_text(url, require_fc2_auth=False)
                    if html is None:
                        with self._lock:
                            self.append_line("error.txt", f"{keyword} -- 连接失败")
                            stats["error"] += 1
                        self.log(f"[{idx + 1}/{len(ids)}] 失败 {keyword}")
                    else:
                        magnet = self.parse_magnet(html)
                        if magnet:
                            with self._lock:
                                self.append_line("magnet.txt", magnet)
                                stats["ok"] += 1
                            self.log(f"[{idx + 1}/{len(ids)}] 命中 {keyword}")
                        else:
                            with self._lock:
                                self.append_line("no_magnet.txt", keyword)
                                stats["no_magnet"] += 1
                            self.log(f"[{idx + 1}/{len(ids)}] 无结果 {keyword}")
                except Exception:
                    with self._lock:
                        self.append_line("error.txt", f"{keyword} -- 未知异常")
                        stats["error"] += 1
                    self.log(f"[{idx + 1}/{len(ids)}] 异常 {keyword}")
                finally:
                    q.task_done()
                    time.sleep(0.5)

        threads = []
        for _ in range(max(1, self.config.max_dl)):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.log(
            "检索完成: "
            f"命中 {stats['ok']} | 无结果 {stats['no_magnet']} | 失败 {stats['error']}"
        )
        return stats
