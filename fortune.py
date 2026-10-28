"""算命 for the group: 八字 from a birth date, a daily 运势 draw, and today's 黄历.

The calendar maths come from lunar-python (github.com/6tail/lunar-python, MIT): the four pillars, their
五行, 十神 and 纳音, the 大运, and the real 黄历 宜/忌 of the day. The model only writes the reading
around those facts. The daily draw follows nonebot_plugin_fortune (github.com/MinatoAquaCrews): one draw
per person per day, the same all day long.
"""
from collections import Counter
from datetime import date
import hashlib
import json
import re

from lunar_python import Lunar, Solar

BAZI = re.compile(r"算命|算八字|测八字|排八字|看八字|批八字|生辰八字|八字排盘|算算命")
DRAW = re.compile(r"今日运势|今天运势|今天的运势|我的运势|看看运势|测运势|测测运势|运势如何|抽签|求签|抽个签|求个签|抽一签|"
                  r"求一签|算一卦|占一卦|占卜一下")
ALMANAC = re.compile(r"黄历|今天宜什么|今日宜忌|今天宜忌|宜忌")
DATE = re.compile(r"(?<!\d)((?:19|20)\d{2})\s*(?:[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})|(\d{2})(\d{2}))(?!\d)")
CLOCK = re.compile(r"(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上|夜里|半夜)?\s*(\d{1,2})\s*(?:[:：]\s*(\d{1,2})|[点时]\s*(?:(\d{1,2})\s*分?|半)?)")
SHICHEN = {"子": 0, "丑": 2, "寅": 4, "卯": 6, "辰": 8, "巳": 10, "午": 12, "未": 14, "申": 16, "酉": 18, "戌": 20, "亥": 22}
# 农历 written in Chinese numerals: "2002年七月初七", "1998年腊月廿三".
LUNAR_DATE = re.compile(r"((?:19|20)\d{2})\s*年?\s*(正|十一|十二|一|二|三|四|五|六|七|八|九|十|冬|腊)月\s*"
                        r"(初[一二三四五六七八九十]|二十|三十|十[一二三四五六七八九]?|廿[一二三四五六七八九])")
DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _lunar_number(text: str) -> int:
    """正/冬/腊 months, and days like 初七 十五 廿三."""
    special = {"正": 1, "冬": 11, "腊": 12, "十一": 11, "十二": 12, "二十": 20, "三十": 30}
    if text in special:
        return special[text]
    if text.startswith("初"):
        return DIGITS[text[1]]
    if text.startswith("廿"):
        return 20 + DIGITS[text[1]]
    if text.startswith("十") and len(text) == 2:
        return 10 + DIGITS[text[1]]
    return DIGITS[text]
ELEMENTS = "金木水火土"
LEVELS = (("大吉", 10), ("中吉", 18), ("小吉", 22), ("吉", 20), ("末吉", 14), ("凶", 11), ("大凶", 5))
COLORS = ("星空蓝", "樱花粉", "薄荷绿", "奶油黄", "香芋紫", "珊瑚橙", "雾霾灰", "天空蓝", "柠檬黄", "酒红色")
BAZI_USAGE = "想算命的话发出生时间给我\n比如“算命 2003-08-01 08:30 男”（阳历，农历就写“农历”）"


FILLER = re.compile(r"星星姐姐|星姐|姐姐|帮我|给我|替我|帮忙|麻烦|请|来|个|一下|看看|我的|我|今天|今日|的|吧|呗|呀|啊|嘛")


def _mostly(pattern: re.Pattern, text: str) -> bool:
    """The message is that request and little else ("帮我抽个签"), not a sentence that mentions it
    ("我们班抽签分组了")."""
    rest = FILLER.sub("", pattern.sub("", text))
    return len(re.sub(r"[^\w]", "", rest)) <= 2


def fortune_request(text: str, called: bool = False):
    """("bazi", birth or None) | ("draw", None) | ("almanac", None), or None for ordinary chat. A birth
    date makes 算命 explicit; otherwise the request has to be the whole message, or said to her."""
    if BAZI.search(text):
        birth = parse_birth(text)
        if birth or called or _mostly(BAZI, text):
            return "bazi", birth
    if DRAW.search(text) and (called or _mostly(DRAW, text)):
        return "draw", None
    if ALMANAC.search(text) and (called or _mostly(ALMANAC, text)):
        return "almanac", None
    return None


def parse_birth(text: str) -> dict | None:
    """A birth date (and maybe a time and a gender) written the way people type it in chat."""
    found = DATE.search(text)
    worded = None if found else LUNAR_DATE.search(text)
    if not found and not worded:
        return None
    if found:
        year = int(found.group(1))
        month, day = ((int(found.group(2)), int(found.group(3))) if found.group(2)
                      else (int(found.group(4)), int(found.group(5))))
    else:
        year, month, day = int(worded.group(1)), _lunar_number(worded.group(2)), _lunar_number(worded.group(3))
    rest = text[(found or worded).end():]
    hour = minute = None
    clock = CLOCK.search(rest)
    if clock:
        period, hour = clock.group(1) or "", int(clock.group(2))
        minute = int(clock.group(3) or clock.group(4) or (30 if "半" in clock.group(0) else 0))
        if period in ("下午", "傍晚", "晚上", "夜里") and hour < 12:
            hour += 12
        elif period == "中午" and hour < 6:
            hour += 12
        elif period == "半夜" and hour == 12:
            hour = 0
    else:
        named = re.search(r"([子丑寅卯辰巳午未申酉戌亥])时", rest)
        if named:
            hour, minute = SHICHEN[named.group(1)], 0
    gender = 1 if re.search(r"男|♂", text) else 0 if re.search(r"女|♀", text) else None
    lunar = bool(worded) or bool(re.search(r"农历|阴历", text))
    if hour is not None and not (0 <= hour <= 23 and 0 <= minute <= 59):
        hour = minute = None
    try:
        if lunar:
            Lunar.fromYmd(year, month, day)
        else:
            date(year, month, day)
    except Exception:
        return None
    if year > date.today().year:
        return None
    return {"year": year, "month": month, "day": day, "hour": hour, "minute": minute or 0,
            "lunar": lunar, "gender": gender}


def bazi_facts(birth: dict) -> dict:
    """The real 排盘: pillars, 五行 count, 日主, 纳音, 十神, 生肖, 星座 and (with a gender) the 大运."""
    hour = birth["hour"] if birth["hour"] is not None else 12
    if birth["lunar"]:
        lunar = Lunar.fromYmdHms(birth["year"], birth["month"], birth["day"], hour, birth["minute"], 0)
        solar = lunar.getSolar()
    else:
        solar = Solar.fromYmdHms(birth["year"], birth["month"], birth["day"], hour, birth["minute"], 0)
        lunar = solar.getLunar()
    chart = lunar.getEightChar()
    pillars = [("年柱", chart.getYear(), chart.getYearWuXing(), chart.getYearShiShenGan(), chart.getYearNaYin()),
               ("月柱", chart.getMonth(), chart.getMonthWuXing(), chart.getMonthShiShenGan(), chart.getMonthNaYin()),
               ("日柱", chart.getDay(), chart.getDayWuXing(), "日主", chart.getDayNaYin())]
    if birth["hour"] is not None:
        pillars.append(("时柱", chart.getTime(), chart.getTimeWuXing(), chart.getTimeShiShenGan(), chart.getTimeNaYin()))
    counts = Counter(element for _, _, elements, _, _ in pillars for element in elements)
    facts = {
        "solar": f"{solar.getYear()}年{solar.getMonth()}月{solar.getDay()}日"
                 + (f" {birth['hour']}:{birth['minute']:02d}" if birth["hour"] is not None else ""),
        "lunar": f"{lunar.getYearInGanZhi()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
                 + (f"{lunar.getTimeZhi()}时" if birth["hour"] is not None else ""),
        "zodiac": lunar.getYearShengXiao(), "star": solar.getXingZuo() + "座",
        "pillars": [{"name": name, "ganzhi": ganzhi, "wuxing": elements, "shishen": god, "nayin": nayin}
                    for name, ganzhi, elements, god, nayin in pillars],
        "counts": {element: counts.get(element, 0) for element in ELEMENTS},
        "missing": [element for element in ELEMENTS if not counts.get(element)],
        "day_master": chart.getDayGan() + chart.getDayWuXing()[0],
        "hour_known": birth["hour"] is not None,
    }
    # Worked out here, not left to the model: it got the current 大运 wrong when asked to count years.
    this_year = date.today().year
    facts["age"] = this_year - solar.getYear()
    facts["this_year"] = Solar.fromYmd(this_year, 7, 1).getLunar().getYearInGanZhi() + "年"
    if birth["gender"] is not None:
        luck = chart.getYun(birth["gender"])
        steps = luck.getDaYun()
        now = next((step for step in steps if step.getStartYear() <= this_year <= step.getEndYear()), None)
        facts["luck"] = {"start": f"{luck.getStartYear()}岁起运",
                         "steps": [f"{step.getStartAge()}岁{step.getGanZhi()}" for step in steps[1:5]],
                         "now": (f"{now.getGanZhi()}（{now.getStartYear()}-{now.getEndYear()}年）"
                                 if now and now.getGanZhi() else "还没起运")}
    return facts


def bazi_prompt(facts: dict, asker: str, owner: bool = False) -> str:
    chart = json.dumps(facts, ensure_ascii=False)
    return (f"群友“{asker}”请你算命。下面是程序按他的出生时间真实排出来的八字（数据不许改，也别编没给的东西）：{chart}\n"
            "你是星姐算命馆的馆主，像一个嘴贫心软、懂点命理的算命先生，一本正经地给他算：结合日主五行、五行多少和缺什么、"
            "十神、纳音、生肖来说，用到术语就顺手用一句大白话解释。今年运势按给出的流年（this_year）和当前大运"
            "（luck.now）来说，年龄看 age，别自己推算；数据里没有的神煞（桃花、驿马、华盖之类）别编。"
            "夸为主，说缺点也说得好听，建议要具体又好笑。"
            "别说寿命、疾病、灾祸、血光这种吓人的话，也别说绝对的话，这是给群友图个乐。"
            + ("他是你主人，多夸他、哄着他说。" if owner else "")
            + ("没给出生时辰，只排了三柱，可以提一句“报上时辰算得更准”。" if not facts["hour_known"] else "")
            + "按 JSON 输出：summary 一句话总评（二十字以内）；personality 性格；career 学业事业；love 感情；wealth 财运；"
              "year 今年运势（这五项每项四十字以内）；advice 星姐的建议（三十字以内）；comment 发命盘时你随口说的一句话（十五字以内）。")


def daily_draw(user_key: str, day: str, owner: bool = False) -> dict:
    """The same draw all day for the same person, like a shrine's one lot a day."""
    seed = int(hashlib.sha256(f"星姐神社|{user_key}|{day}".encode("utf-8")).hexdigest(), 16)
    roll, level = seed % 100, LEVELS[-1][0]
    for name, weight in LEVELS:
        if roll < weight:
            level = name
            break
        roll -= weight
    if owner and level in ("凶", "大凶"):
        level = "小吉"  # her owner's day is never a bad one
    return {"level": level, "number": seed // 100 % 99 + 1, "color": COLORS[seed // 10000 % len(COLORS)]}


def almanac(day: date | None = None) -> dict:
    """Today's real 黄历."""
    day = day or date.today()
    lunar = Solar.fromYmd(day.year, day.month, day.day).getLunar()
    coming = lunar.getNextJieQi()
    return {"solar": f"{day.year}年{day.month}月{day.day}日",
            "lunar": f"农历{lunar.getYearInGanZhi()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}",
            "ganzhi": lunar.getDayInGanZhi() + "日", "yi": list(lunar.getDayYi()), "ji": list(lunar.getDayJi()),
            "chong": f"冲{lunar.getDayChongShengXiao()}（{lunar.getDayChongGan()}{lunar.getDayChong()}）",
            "sha": "煞" + lunar.getDaySha(), "jieqi": lunar.getJieQi(),
            "next_jieqi": f"{coming.getName()}（{coming.getSolar().getMonth()}月{coming.getSolar().getDay()}日）"}


def almanac_text(day: dict) -> str:
    return "\n".join([f"{day['solar']} {day['lunar']} {day['ganzhi']}",
                      "宜：" + " ".join(day["yi"][:8]), "忌：" + " ".join(day["ji"][:8]),
                      f"{day['chong']} {day['sha']}"
                      + (f" 今天{day['jieqi']}" if day["jieqi"] else f" 下一个节气{day['next_jieqi']}")])


def draw_prompt(draw: dict, day: dict, asker: str, owner: bool = False) -> str:
    facts = json.dumps({"运势": draw["level"], "宜": day["yi"][:6], "忌": day["ji"][:6]}, ensure_ascii=False)
    return (f"群友“{asker}”在星姐神社抽了今天的签：{facts}（运势和宜忌是定好的，不许改）。你是神社的巫女星姐，"
            "给他写这支签：poem 是两句签诗（每句七个字左右，可以押韵，要贴合这个运势）；meaning 是解签（四十字以内，"
            "说说今天会怎样，具体又好笑，坏签也要说得让人想笑而不是难过）；advice 是今天的一句小建议（二十四字以内）；"
            "comment 是递签时你随口说的一句话（十五字以内）。" + ("他是你主人，多哄着点。" if owner else "")
            + "按 JSON 输出。")


def clip(text: str, limit: int) -> str:
    """Cut at the last clause end within `limit`, so a card never stops in the middle of a word."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    cut = max(head.rfind(mark) for mark in "。！？；，,.!?;")
    return head[:cut] if cut >= limit // 2 else head[:limit - 1] + "…"


def parse_reading(raw: str | None, fields: dict[str, int]) -> dict | None:
    """The model's JSON with each field clipped to its length; None when the required text is missing."""
    try:
        data = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip()))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    reading = {name: clip(re.sub(r"\s+", " ", str(data.get(name) or "")).strip(), limit)
               for name, limit in fields.items()}
    return reading if all(reading[name] for name in list(fields)[:2]) else None


BAZI_FIELDS = {"summary": 30, "personality": 60, "career": 60, "love": 60, "wealth": 60, "year": 60, "advice": 44,
               "comment": 24}
DRAW_FIELDS = {"poem": 30, "meaning": 50, "advice": 32, "comment": 24}


def fallback_bazi(facts: dict) -> dict:
    missing = "、".join(facts["missing"])
    return {"summary": f"{facts['day_master']}命 {'五行缺' + missing if missing else '五行齐全'}",
            "personality": "", "career": "", "love": "", "wealth": "", "year": "",
            "advice": "命盘先拿好 解读星姐晚点补上", "comment": "命盘排好了"}


def fallback_draw(draw: dict) -> dict:
    return {"poem": "今日签文未落笔 星姐先替你保密", "meaning": f"今天是{draw['level']}，具体的等星姐缓过来再解",
            "advice": f"带点{draw['color']}出门", "comment": "签抽好了"}
