"""Optional Qzone text posts via NapCat get_cookies; isolated from group chat.

Qzone's unofficial publish endpoint and request parameters can change at any time.
Keep this feature disabled by default. Failures are logged and never affect group chat.
"""
import asyncio
import logging
import re

import requests

LOG = logging.getLogger(__name__)


def g_tk(cookie: str) -> int:
    match = re.search(r"(?:^|;\s*)p_skey=([^;]+)", cookie)
    if not match:
        match = re.search(r"(?:^|;\s*)skey=([^;]+)", cookie)
    if not match:
        raise ValueError("Cookie 缺少 p_skey/skey")
    value = 5381
    for char in match.group(1):
        value += (value << 5) + ord(char)
    return value & 0x7fffffff


def _publish(url: str, cookie: str, uin: int, text: str, timeout: float) -> bool:
    params = {"g_tk": g_tk(cookie)}
    data = {"con": text, "syn_tweet_version": "1", "paramstr": "1", "feedversion": "1",
            "ver": "1", "ugc_right": "1", "to_sign": "0", "hostuin": str(uin),
            "code_version": "1", "format": "json",
            "qzreferrer": f"https://user.qzone.qq.com/{uin}"}
    response = requests.post(url, params=params, data=data,
                             headers={"Cookie": cookie, "Referer": f"https://user.qzone.qq.com/{uin}",
                                      "User-Agent": "Mozilla/5.0"}, timeout=timeout)
    response.raise_for_status()
    result = response.json()
    return result.get("code") == 0


async def post_qzone(bot, text: str) -> bool:
    if not bot.config["qzone_enabled"]:
        return False
    try:
        result = await bot.call_api("get_cookies", {"domain": "qzone.qq.com"})
        data = result.get("data") or {}
        cookie = data if isinstance(data, str) else data.get("cookies", "")
        if not cookie:
            raise ValueError("NapCat 没有返回 qzone.qq.com Cookie")
        success = await asyncio.to_thread(_publish, bot.config["qzone_publish_url"], cookie,
                                          bot.self_id, text, float(bot.config["qzone_timeout_seconds"]))
        if not success:
            LOG.warning("QQ 空间接口未确认发布成功")
        return success
    except Exception:
        LOG.exception("QQ 空间发布失败，群聊继续运行")
        return False
