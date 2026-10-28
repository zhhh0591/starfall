"""Occasional Star Sister fan art. Image failures never escape this module."""
import base64
import io
import logging
from pathlib import Path
import random

from PIL import Image

LOG = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent
APPEARANCE = ("星姐，蓝紫渐变长发，猫耳，四角星发卡，异色瞳（左眼粉红、右眼金黄），"
              "星星主题深蓝紫色服装和星星配饰，蓝紫色尾巴，Q版大头小身，扁平动漫感，干净线条，白色背景")


def _local_gallery(bot) -> list[Path]:
    configured = Path(bot.config.get("fanart_directory", "fanart")).expanduser()
    directory = configured if configured.is_absolute() else ROOT / configured
    if not directory.is_dir():
        return []
    maximum = int(bot.config.get("fanart_max_file_mb", 8)) * 1024 * 1024
    return sorted(path for path in directory.iterdir()
                  if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
                  and 0 < path.stat().st_size <= maximum)


def _choose_local(bot, files: list[Path], preferred: str | None = None) -> Path:
    names = {path.name for path in files}
    remaining = [name for name in bot.state.get("fanart_remaining", []) if name in names]
    if not remaining:
        remaining = sorted(names)
        random.shuffle(remaining)
        last = bot.state.get("fanart_last_name")
        if len(remaining) > 1 and remaining[-1] == last:
            remaining[0], remaining[-1] = remaining[-1], remaining[0]
    if preferred in remaining and preferred != bot.state.get("fanart_last_name"):
        index = remaining.index(preferred)
        remaining[index], remaining[-1] = remaining[-1], remaining[index]
    bot.state["fanart_remaining"] = remaining
    return next(path for path in files if path.name == remaining[-1])


def _contextual_meme(bot, group_id: int, files: list[Path]) -> str | None:
    keywords = bot.config.get("meme_keywords", {})
    available = {path.stem: path.name for path in files}
    for item in reversed(list(bot.memory[group_id])[-8:]):
        text = item.get("text", "")
        for stem, words in keywords.items():
            if stem in available and any(word in text for word in words):
                return available[stem]
    return None


async def post_local_image(bot, group_id: int) -> bool | None:
    """None means no local art; False means an attempted upload failed."""
    try:
        files = _local_gallery(bot)
    except Exception as exc:
        LOG.warning("本地二创图库无法读取：%s", exc)
        return False
    if not files:
        return None
    path = _choose_local(bot, files, _contextual_meme(bot, group_id, files))
    try:
        with Image.open(path) as source:
            source.verify()
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        captions = bot.config.get("fanart_captions", {})
        caption = str(captions.get(path.stem, "给你们看张星姐的梗图～"))
        message = [{"type": "text", "data": {"text": caption}},
                   {"type": "image", "data": {"file": "base64://" + encoded}}]
        if not await bot.send_group(group_id, message):
            return False
        bot.state["fanart_remaining"].pop()
        bot.state["fanart_last_name"] = path.name
        bot.state["fanart_posted"] = True
        bot.persist()
        LOG.info("群 %s 已发送本地二创图 %s", group_id, path.name)
        return True
    except Exception as exc:
        LOG.warning("本地二创图 %s 发送失败，安静跳过：%s", path.name, exc)
        return False


async def post_image(bot, group_id: int) -> bool:
    if bot.config.get("fanart_local_enabled", True):
        local_result = await post_local_image(bot, group_id)
        if local_result is not None:
            return local_result
    if not bot.config.get("fanart_gemini_fallback_enabled", True):
        return False
    theme = random.choice(bot.config["image_themes"])
    prompt = (f"画一张原创 Q 版双格中文群聊梗图：{APPEARANCE}。"
              f"情景主题：{theme}。用夸张反应和意外转折形成轻松笑点，避免攻击或羞辱别人。"
              "保持以上外貌完全一致。画面清楚、完整、短文字、无水印。")
    try:
        image_bytes = await bot.gemini.image(prompt)
        if not image_bytes:
            LOG.info("图片请求没有返回图像，跳过")
            return False
        with Image.open(io.BytesIO(image_bytes)) as source:
            converted = source.convert("RGB")
            output = io.BytesIO()
            converted.save(output, format="PNG", optimize=True)
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        # OneBot 11 image segment supports base64:// payloads.
        message = [{"type": "text", "data": {"text": f"星姐的小画：{theme}～"}},
                   {"type": "image", "data": {"file": "base64://" + encoded}}]
        return await bot.send_group(group_id, message)
    except Exception:
        LOG.exception("二创图生成或发送失败，已安静跳过")
        return False
