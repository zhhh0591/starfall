"""Pure message parsing, prompt-injection guard, and reply formatting."""
from difflib import SequenceMatcher
import json
import re

INJECTION_PATTERNS = (
    r"忽略.{0,12}(之前|以上|设定|指令|提示)",
    r"你现在是", r"从现在起你是", r"扮演.{0,12}(角色|身份)",
    r"(system\s*prompt|system\s*instruction|developer\s*message)",
    r"(无视|覆盖|修改).{0,12}(系统|人设|规则|提示词)",
    r"(越狱|jailbreak|ignore\s+(all\s+)?previous)",
)
REFUSAL = "想让我换人设啊 这招我见多了\n我还是星姐 有事说事"
CALL_NAMES = re.compile(r"星星姐姐|星姐|姐姐")
ADMIN_PREFIXES = ("/人设", "/记忆", "/主动发言", "/频率", "/休眠", "/唤醒", "/额度", "/换头像", "/头像", "/语料")
HARASSMENT_PATTERNS = (
    r"(你|他|她|它|@).{0,12}(真蠢|太蠢|废物|垃圾|闭嘴|滚开|去死)",
    r"(没人喜欢你|你不配|你真没用|活该被|少在这装|阴阳怪气)",
)


# 星姐 never swears, even when answering the evil bot; a reply with any of these is rewritten or dropped.
CRUDE = re.compile(r"喷粪|吃屎|放屁|傻[逼Bb比Xx叉]|煞笔|沙比|[他她你]妈|妈的|尼玛|狗东西|狗日|滚蛋|去死|脑残|智障|操你|艹|卧槽|贱人|废物东西"
                   r"|泔水|垃圾桶里|粪坑|狗嘴|畜生|猪脑|猪狗不如")


def is_crude(text: str) -> bool:
    return bool(CRUDE.search(text or ""))


def is_injection(text: str) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in INJECTION_PATTERNS)


def is_admin_command(text: str) -> bool:
    return text.strip().startswith(ADMIN_PREFIXES)


def is_harassment(text: str) -> bool:
    """Conservative trigger; Gemini handles context and tone after this check."""
    return any(re.search(pattern, text, re.I) for pattern in HARASSMENT_PATTERNS)


def is_called(text: str, segments: list, self_id: int) -> bool:
    if CALL_NAMES.search(text):
        return True
    return any(seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == str(self_id)
               for seg in segments)


def plain_text(message) -> str:
    if isinstance(message, str):
        return re.sub(r"\[CQ:[^\]]+\]", "", message).strip()
    if isinstance(message, list):
        return "".join(str(seg.get("data", {}).get("text", "")) for seg in message
                       if isinstance(seg, dict) and seg.get("type") == "text").strip()
    return ""


def segments(message) -> list:
    if isinstance(message, list):
        return [part for part in message if isinstance(part, dict)]
    if isinstance(message, str):
        return [{"type": "at", "data": {"qq": match}}
                for match in re.findall(r"\[CQ:at,qq=(\d+)\]", message)]
    return []


def clean_reply(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text or "")
    text = re.sub(r"(?m)^\s*(?:#{1,6}|[-*•]|\d+[.)、])\s*", "", text)
    text = re.sub(r"[*_`#]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:150].rstrip("，、；：")


def split_reply_bubbles(text: str, max_chars: int = 65, total_chars: int = 130,
                        max_bubbles: int = 2) -> list[str]:
    """Turn a short answer into one or two natural QQ messages."""
    text = clean_reply(text)[:total_chars].strip()
    if not text or max_bubbles < 1:
        return []
    bubbles = []
    while text and len(bubbles) < max_bubbles:
        if len(text) <= max_chars or len(bubbles) == max_bubbles - 1:
            bubbles.append(text)
            break
        minimum_cut = max(1, len(text) - max_chars * (max_bubbles - len(bubbles) - 1))
        choices = [m.end() for m in re.finditer(r"[。！？!?；;，,]", text[:max_chars])
                   if m.end() >= minimum_cut]
        cut = choices[-1] if choices else max_chars
        bubbles.append(text[:cut].strip())
        text = text[cut:].strip()
    return [item for item in bubbles if item]


SKIP_TAG = re.compile(r"\[\s*SKIP\s*\]", re.I)
STICKER_TAG = re.compile(r"\[表情[:：]\s*([^\[\]\n]{1,8})\]")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")
ASIDE = re.compile(r"[（(][^（）()\n]{1,6}[）)]|\*[^*\n]{1,8}\*")
SPEAKER = re.compile(r"^\s*(星姐|星星姐姐)\s*[:：]\s*")
# The chat log tags names with [主人] / [邪恶人格]; those tags are for her, never for the group.
ROLE_TAG = re.compile(r"\[(主人|邪恶人格)\]")


def _split_line(line: str, max_chars: int, slots: int) -> list[str]:
    pieces = []
    while line and slots > 0:
        if len(line) <= max_chars or slots == 1:
            pieces.append(line[:max_chars * 2])
            break
        cuts = [m.end() for m in re.finditer(r"[。！？!?；;，, ]", line[:max_chars + 1]) if m.end() > 1]
        cut = cuts[-1] if cuts else max_chars
        pieces.append(line[:cut])
        line = line[cut:].strip()
        slots -= 1
    return pieces


def parse_reply(text: str, max_chars: int = 40, total_chars: int = 120,
                max_bubbles: int = 3) -> tuple[list[str], str | None, bool]:
    """Model output -> (chat bubbles, sticker keyword, skip). One output line is one QQ message."""
    text = re.sub(r"```[\s\S]*?```", "", text or "")
    if SKIP_TAG.search(text):
        return [], None, True
    keyword = None
    match = STICKER_TAG.search(text)
    if match:
        keyword = match.group(1).strip() or None
        text = STICKER_TAG.sub("", text)
    bubbles, used = [], 0
    for raw in text.splitlines():
        line = ROLE_TAG.sub(lambda match: "主人" if match.group(1) == "主人" else "", SPEAKER.sub("", raw))
        line = re.sub(r"^\s*(?:#{1,6}|[-*•]|\d+[.)、])\s+", "", line)
        line = EMOJI.sub("", ASIDE.sub("", line))
        line = re.sub(r"[*_`#]", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        for piece in _split_line(line, max_chars, max_bubbles - len(bubbles)):
            piece = piece.strip().rstrip("。，、；：,;").replace("。", " ").strip()
            if not piece or used >= total_chars:
                continue
            piece = piece[:total_chars - used]
            bubbles.append(piece)
            used += len(piece)
        if len(bubbles) >= max_bubbles:
            break
    return bubbles, keyword, False


def parse_brainstorm(text: str) -> tuple[bool, list[tuple[str, str]]]:
    """The three-angle answer {"skip", "angles": [{"angle", "reply"}], "best"} as (skip, [(angle, reply)])
    with the model's pick first. Plain text gives (False, []) and is used as an ordinary reply; JSON that
    is broken (cut off at the token limit) keeps its complete replies, or counts as nothing to say, so
    raw JSON never reaches the group."""
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    if not raw.startswith("{"):
        return False, []
    try:
        data = json.loads(raw)
    except ValueError:
        replies = []
        for match in re.finditer(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', raw):
            try:
                replies.append(("", json.loads(f'"{match.group(1)}"')))
            except ValueError:
                pass
        data = {"angles": [{"angle": angle, "reply": reply} for angle, reply in replies], "best": 1}
    if not isinstance(data, dict) or data.get("skip") is True:
        return True, []
    angles = [(str(item.get("angle") or "").strip(), str(item.get("reply") or "").strip())
              for item in data.get("angles") or [] if isinstance(item, dict)]
    angles = [(angle, reply) for angle, reply in angles if reply and not SKIP_TAG.search(reply)]
    if not angles:
        return True, []
    best = data.get("best")
    index = best - 1 if isinstance(best, int) and 1 <= best <= len(angles) else 0
    return False, [angles[index]] + angles[:index] + angles[index + 1:]


def reply_similarity(text: str, recent_replies: list[str]) -> float:
    """Highest similarity to recent bot messages, ignoring punctuation and spacing."""
    candidate = re.sub(r"[\W_]", "", clean_reply(text))
    if not candidate:
        return 0.0
    scores = []
    for previous in recent_replies:
        previous = re.sub(r"[\W_]", "", previous)
        if previous:
            scores.append(SequenceMatcher(None, candidate, previous).ratio())
    return max(scores, default=0.0)
