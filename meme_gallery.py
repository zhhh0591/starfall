"""Search a Chinese sticker gallery for one image related to the current reply."""
import asyncio
import io
import logging
import random
import re
import time
from urllib.parse import urlparse

import jieba.analyse
from PIL import Image
import requests

LOG = logging.getLogger(__name__)
TOPICS = (
    (r"作业|考试|题目|做题|数学|学习|复习", "作业"),
    (r"代码|程序|编程|报错|部署|服务器|bug|Bug", "程序员"),
    (r"睡觉|晚安|困了|困死|熬夜|失眠", "困了"),
    (r"上班|工作|打工|摸鱼|加班", "摸鱼"),
    (r"吃饭|饿了|午饭|晚饭|早餐|奶茶", "吃饭"),
    (r"开心|高兴|成功|恭喜|赢了", "开心"),
    (r"难过|伤心|委屈|焦虑|压力", "安慰"),
    (r"下雨|雨天|天气|带伞", "下雨"),
    (r"机器人|模型|AI|人工智能|电量|充电", "机器人"),
    (r"唱歌|音乐|歌曲|听歌", "唱歌"),
)
SKIP_WORDS = {"星姐", "星星姐姐", "姐姐", "群友", "今天", "这个", "那个", "一下", "什么", "怎么", "可以", "还是", "就是", "真的", "自己", "我们", "你们", "他们", "消息", "回复"}
ALLOWED_IMAGE_HOST = "biaoqing.gtimg.com"


def query_for_dialogue(message: str, answer: str) -> str:
    """Send a topic word, never a raw group transcript or account number."""
    clean = re.sub(r"https?://\S+|\d{5,}|\[CQ:[^]]*]", " ", message)
    clean = clean.replace("星星姐姐", " ").replace("星姐", " ")[:160]
    for pattern, query in TOPICS:
        if re.search(pattern, clean, re.I):
            return query
    words = jieba.analyse.extract_tags(clean + " " + answer[:80], topK=12)
    for word in words:
        if (2 <= len(word) <= 6 and word not in SKIP_WORDS
                and re.fullmatch(r"[\u4e00-\u9fff]+", word)):
            return word
    return "聊天"


class MemeGallery:
    def __init__(self, config: dict):
        self.config = config
        self.day = ""
        self.calls_today = 0
        self.last_url = {}

    def _fetch(self, query: str, group_id: int) -> bytes | None:
        endpoint = self.config.get("meme_gallery_search_url", "https://itapi.top/api/bqss")
        if urlparse(endpoint).scheme != "https" or urlparse(endpoint).hostname != "itapi.top":
            LOG.warning("图库搜索地址不受支持")
            return None
        timeout = float(self.config.get("meme_gallery_timeout_seconds", 8))
        count = max(1, min(20, int(self.config.get("meme_gallery_result_count", 12))))
        response = requests.get(endpoint, params={"msg": query, "page": 1, "num": count},
                                timeout=timeout, allow_redirects=False)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            return None
        options = [item.get("sticker_url") for item in payload.get("data") or []
                   if isinstance(item, dict) and isinstance(item.get("sticker_url"), str)]
        previous = self.last_url.get(group_id)
        options = [url for url in options if url != previous] or options
        random.shuffle(options)
        maximum = int(self.config.get("meme_gallery_max_file_mb", 3)) * 1024 * 1024
        for url in options[:3]:
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname != ALLOWED_IMAGE_HOST:
                continue
            try:
                with requests.get(url, timeout=timeout, stream=True, allow_redirects=False) as image_response:
                    image_response.raise_for_status()
                    if int(image_response.headers.get("Content-Length", 0)) > maximum:
                        continue
                    data = bytearray()
                    for chunk in image_response.iter_content(65536):
                        data.extend(chunk)
                        if len(data) > maximum:
                            break
                    if len(data) > maximum or len(data) < 1000:
                        continue
                with Image.open(io.BytesIO(data)) as picture:
                    if picture.format not in {"PNG", "JPEG", "GIF", "WEBP"}:
                        continue
                    if not (50 <= picture.width <= 3000 and 50 <= picture.height <= 3000):
                        continue
                    picture.verify()
                self.last_url[group_id] = url
                return bytes(data)
            except Exception as exc:
                LOG.info("图库候选图片不可用：%s", exc)
        return None

    async def find(self, group_id: int, message: str, answer: str, query: str | None = None) -> bytes | None:
        """`query` is the model's own [表情:词] keyword; otherwise a topic word is guessed from the chat."""
        if not self.config.get("meme_gallery_enabled", False):
            return None
        today = time.strftime("%Y-%m-%d")
        if today != self.day:
            self.day, self.calls_today = today, 0
        limit = int(self.config.get("meme_gallery_daily_limit", 100))
        if self.calls_today >= limit:
            return None
        self.calls_today += 1
        query = re.sub(r"[^\w一-鿿]", "", query or "")[:8] or query_for_dialogue(message, answer)
        try:
            result = await asyncio.to_thread(self._fetch, query, group_id)
            LOG.info("群 %s 图库检索关键词：%s，%s", group_id, query, "找到图片" if result else "没有可用图片")
            return result
        except Exception as exc:
            LOG.warning("图库搜索失败，文字回复照常发送：%s", exc)
            return None
