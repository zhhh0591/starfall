"""Small, optional public web search for time-sensitive group questions."""
import asyncio
import base64
from datetime import datetime
from html.parser import HTMLParser
import logging
import re
import time
from urllib.parse import parse_qs, urlparse

import requests

LOG = logging.getLogger(__name__)
SEARCH_URL = "https://lite.duckduckgo.com/lite/"
BING_URL = "https://www.bing.com/search"
SO_URL = "https://www.so.com/s"


def needs_web_search(text: str) -> bool:
    """Search only when the message asks for outside or changing information."""
    if re.search(r"(别|不要|不用|无需).{0,3}(联网|搜索|上网|查网)", text):
        return False
    if re.search(r"(联网|上网|搜一下|搜搜|搜索|查一下|查查|网上查|查资料)", text):
        return True
    # "现在回答我…" orders her to answer now; it does not ask about anything current.
    changing = r"(今天|明天|现在(?!就|马上|立刻|赶紧|快|回答|告诉|说|给|帮|跟)|目前|刚刚|最近|最新|实时|本周|今年|20\d{2})"
    subject = r"(天气|气温|新闻|消息|新鲜事|价格|票价|汇率|股价|比赛|赛程|政策|规定|发布|上映|活动|开放|营业|排名|谁|多少|几点|什么时候|推荐|哪个好)"
    return bool(re.search(changing, text) and re.search(subject, text))


class _LiteParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self.mode = None
        self.buffer = []
        self.href = ""

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag == "a" and "result-link" in classes:
            self.mode, self.buffer, self.href = "title", [], values.get("href") or ""
        elif tag == "td" and "result-snippet" in classes:
            self.mode, self.buffer = "snippet", []

    def handle_data(self, data):
        if self.mode:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.mode == "title":
            title = " ".join("".join(self.buffer).split())
            url = _unwrap_url(self.href)
            if title and url:
                self.results.append({"title": title[:120], "url": url, "snippet": ""})
            self.mode = None
        elif tag == "td" and self.mode == "snippet":
            if self.results:
                self.results[-1]["snippet"] = " ".join("".join(self.buffer).split())[:400]
            self.mode = None


def _unwrap_url(href: str) -> str | None:
    parsed = urlparse(href if not href.startswith("//") else "https:" + href)
    if parsed.netloc.endswith("duckduckgo.com"):
        href = parse_qs(parsed.query).get("uddg", [""])[0]
        parsed = urlparse(href)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return href[:500]


def _unwrap_bing_url(href: str) -> str | None:
    parsed = urlparse(href)
    if parsed.hostname == "www.bing.com" and parsed.path == "/ck/a":
        token = parse_qs(parsed.query).get("u", [""])[0]
        if token.startswith("a1"):
            try:
                href = base64.urlsafe_b64decode(token[2:] + "=" * (-len(token[2:]) % 4)).decode("utf-8")
            except Exception:
                return None
    return _unwrap_url(href)


class _BingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self.depth = 0
        self.in_h2 = False
        self.mode = None
        self.buffer = []
        self.current = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag == "li":
            if self.depth:
                self.depth += 1
            elif "b_algo" in classes:
                self.depth = 1
                self.current = {}
        if not self.depth:
            return
        if tag == "h2":
            self.in_h2 = True
        elif tag == "a" and self.in_h2:
            self.current["url"] = _unwrap_bing_url(values.get("href") or "")
            self.mode, self.buffer = "title", []
        elif tag == "p" and any(name.startswith("b_lineclamp") for name in classes):
            self.mode, self.buffer = "snippet", []

    def handle_data(self, data):
        if self.mode:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.mode == "title":
            self.current["title"] = " ".join("".join(self.buffer).split())[:120]
            self.mode = None
        elif tag == "p" and self.mode == "snippet":
            self.current["snippet"] = " ".join("".join(self.buffer).split())[:400]
            self.mode = None
        elif tag == "h2":
            self.in_h2 = False
        elif tag == "li" and self.depth:
            self.depth -= 1
            if self.depth == 0 and self.current.get("url") and self.current.get("title"):
                self.current.setdefault("snippet", "")
                self.results.append(self.current)
                self.current = {}


class _SoParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self.depth = 0
        self.in_title = False
        self.mode = None
        self.buffer = []
        self.current = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag == "li":
            if self.depth:
                self.depth += 1
            elif "res-list" in classes:
                self.depth, self.current = 1, {}
        if not self.depth:
            return
        if tag == "h3" and "res-title" in classes:
            self.in_title = True
        elif tag == "a" and self.in_title:
            self.current["url"] = _unwrap_url(values.get("data-mdurl") or "")
            self.mode, self.buffer = "title", []
        elif tag == "span" and "data-result-summary" in values:
            self.mode, self.buffer = "snippet", []

    def handle_data(self, data):
        if self.mode:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.mode == "title":
            self.current["title"] = " ".join("".join(self.buffer).split())[:120]
            self.mode = None
        elif tag == "span" and self.mode == "snippet":
            self.current["snippet"] = " ".join("".join(self.buffer).split())[:400]
            self.mode = None
        elif tag == "h3":
            self.in_title = False
        elif tag == "li" and self.depth:
            self.depth -= 1
            if self.depth == 0 and self.current.get("url") and self.current.get("title"):
                self.current.setdefault("snippet", "")
                self.results.append(self.current)
                self.current = {}


class WebSearch:
    def __init__(self, config: dict):
        self.config = config
        self.cache = {}
        self.day = ""
        self.today_count = 0

    def _fetch(self, query: str) -> list[dict]:
        timeout = float(self.config.get("web_search_timeout_seconds", 8))
        headers = {"User-Agent": "Mozilla/5.0 (compatible; QQStarSister/1.0)"}
        try:
            response = requests.get(self.config.get("web_search_url", SEARCH_URL), params={"q": query},
                                    headers=headers, timeout=timeout)
            response.raise_for_status()
            parser = _LiteParser()
            parser.feed(response.text)
            if parser.results:
                return parser.results[:int(self.config.get("web_search_max_results", 3))]
        except Exception as exc:
            LOG.info("DuckDuckGo 检索不可用，尝试备用入口：%s", exc)
        try:
            response = requests.get(SO_URL, params={"q": query},
                                    headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
            response.raise_for_status()
            parser = _SoParser()
            parser.feed(response.text)
            if parser.results:
                return parser.results[:int(self.config.get("web_search_max_results", 3))]
        except Exception as exc:
            LOG.info("360 搜索不可用，尝试备用入口：%s", exc)
        response = requests.get(BING_URL, params={"q": query}, headers={"User-Agent": "Mozilla/5.0"},
                                timeout=timeout)
        response.raise_for_status()
        parser = _BingParser()
        parser.feed(response.text)
        return parser.results[:int(self.config.get("web_search_max_results", 3))]

    async def search(self, query: str) -> list[dict]:
        query = re.sub(r"(?:星星姐姐|星姐|姐姐|\[CQ:[^\]]+\])", "", query).strip()[:120]
        if not query:
            return []
        if re.search(r"(今天|明天|现在|最新|最近|本周)", query) and not re.search(r"20\d{2}", query):
            query += " " + datetime.now().strftime("%Y-%m-%d")
        today = time.strftime("%Y-%m-%d")
        if today != self.day:
            self.day, self.today_count = today, 0
            self.cache.clear()
        now = time.time()
        cached = self.cache.get(query)
        if cached and now - cached[0] < float(self.config.get("web_search_cache_minutes", 20)) * 60:
            return cached[1]
        if self.today_count >= int(self.config.get("web_search_daily_limit", 30)):
            LOG.info("今日网页检索次数已达上限")
            return []
        self.today_count += 1
        try:
            results = await asyncio.to_thread(self._fetch, query)
            if results:
                self.cache[query] = (now, results)
            LOG.info("网页检索完成：%d 条结果", len(results))
            return results
        except Exception as exc:
            LOG.warning("网页检索失败：%s", exc)
            return []
