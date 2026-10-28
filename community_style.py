"""Fresh Chinese community snippets as untrusted style inspiration, never copy."""
from difflib import SequenceMatcher
import logging
import random
import re
from urllib.parse import urlparse

from guardian import is_harassment, is_injection
from meme_gallery import query_for_dialogue
from web_search import WebSearch

LOG = logging.getLogger(__name__)
COMMUNITIES = ("zhihu.com", "tieba.baidu.com")
PROMOTION = re.compile(r"微信群|加群|私信|下载地址|扫码|推广|公众号|广告|付费课程")


def _allowed(url: str, site: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == site or (site == "zhihu.com" and host.endswith(".zhihu.com"))


def too_close_to_source(answer: str, sources: list[dict], minimum: int = 9) -> bool:
    """Flag copied stretches from public search snippets before a reply is sent."""
    candidate = re.sub(r"[\W_]", "", answer)
    if len(candidate) < minimum:
        return False
    for item in sources:
        reference = re.sub(r"[\W_]", "", item.get("snippet", ""))
        if not reference:
            continue
        match = SequenceMatcher(None, candidate, reference, autojunk=False).find_longest_match(
            0, len(candidate), 0, len(reference))
        if match.size >= max(minimum, len(candidate) // 2):
            return True
    return False


def topic_terms(message: str) -> str:
    text = re.sub(r"https?://\S+|\d{5,}", " ", message)
    if "作业" in text and re.search(r"写不完|太多|好多|做不完", text):
        return "作业 写不完"
    if re.search(r"上班|工作|加班", text) and re.search(r"累|烦|困|摸鱼", text):
        return "上班 累"
    if re.search(r"机器人|AI|模型", text) and re.search(r"重复|一样|总说|老说", text):
        return "机器人 回复 重复"
    return query_for_dialogue(text, "")


class CommunityStyle:
    def __init__(self, config: dict):
        self.config = config
        search_config = {**config,
                         "web_search_max_results": int(config.get("community_style_max_results", 2)),
                         "web_search_daily_limit": int(config.get("community_style_daily_limit", 100)),
                         "web_search_cache_minutes": 0,
                         "web_search_timeout_seconds": float(config.get("community_style_timeout_seconds", 8))}
        self.searcher = WebSearch(search_config)

    async def search(self, message: str) -> list[dict]:
        if not self.config.get("community_style_enabled", False):
            return []
        topic = topic_terms(message)
        if topic == "聊天" and len(message.strip()) < 4:
            topic = "日常聊天"
        sites = list(COMMUNITIES)
        random.shuffle(sites)
        for site in sites:
            query = f"site:{site} {topic} 吐槽"
            results = await self.searcher.search(query)
            selected = [dict(title=item.get("title", "")[:70],
                             snippet=item.get("snippet", "")[:160])
                        for item in results if _allowed(item.get("url", ""), site)
                        and len(item.get("snippet", "")) >= 15
                        and not PROMOTION.search(item.get("title", "") + item.get("snippet", ""))
                        and not is_harassment(item.get("snippet", ""))
                        and not is_injection(item.get("snippet", ""))]
            if selected:
                LOG.info("中文社区表达参考：%s，%d 条", site, len(selected))
                return selected
        return []
