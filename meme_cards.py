"""Picture memes 星姐 draws herself (no downloads, no API calls): a 低情商/高情商 comparison card.

The model asks for one with a line like [高情商:你们都是废物|大家各有各的可爱].
"""
import io
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps

EQ_TAG = re.compile(r"\[高情商[:：]\s*([^\[\]|｜\n]{1,40})[|｜]\s*([^\[\]\n]{1,40})\]")
FONTS = ("/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
         "/System/Library/Fonts/Supplemental/Arial Unicode.ttf")


LABEL = re.compile(r"^\s*(低情商|高情商)\s*[:：]\s*")


def extract_eq_card(text: str) -> tuple[str, tuple[str, str] | None]:
    match = EQ_TAG.search(text or "")
    if not match:
        return text, None
    low, high = match.group(1).strip(), match.group(2).strip()
    # Models sometimes write it the other way round: [高情商:高情商说法|低情商:原话].
    second = LABEL.match(high)
    if second and second.group(1) == "低情商":
        low, high = high, low
    low, high = LABEL.sub("", low).strip(), LABEL.sub("", high).strip()
    return EQ_TAG.sub("", text), ((low, high) if low and high and low != high else None)


def _font(size: int):
    for path in FONTS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for char in text:
        if draw.textlength(line + char, font=font) > width and line:
            lines.append(line)
            line = char
        else:
            line += char
    return lines + [line] if line else lines


CLOSING_MARKS = "，。！？、；：”’）」』》…,.!?;:)"


def _wrap_cjk(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    """_wrap, but a line never starts with a closing mark (it stays at the end of the line before), and
    the last line is never one or two lonely characters."""
    lines = _wrap(draw, text, font, width)
    for index in range(1, len(lines)):
        while lines[index] and lines[index][0] in CLOSING_MARKS:
            lines[index - 1] += lines[index][0]
            lines[index] = lines[index][1:]
    lines = [line for line in lines if line]
    if len(lines) > 1 and len(lines[-1]) <= 2 and len(lines[-2]) > 4:
        lines[-2], lines[-1] = lines[-2][:-2], lines[-2][-2:] + lines[-1]
    return lines


def _heart(draw: ImageDraw.ImageDraw, center: tuple[int, int], size: int, fill):
    """Drawn, not typed: the CJK font has no heart glyph."""
    x, y = center
    radius = size // 4
    draw.ellipse((x - 2 * radius, y - radius - radius // 2, x, y + radius // 2), fill=fill)
    draw.ellipse((x, y - radius - radius // 2, x + 2 * radius, y + radius // 2), fill=fill)
    draw.polygon([(x - 2 * radius + 1, y + 1), (x + 2 * radius - 1, y + 1), (x, y + 2 * radius + radius // 2)], fill=fill)


def _avatar_disc(card: Image.Image, avatar: Path | None, position: tuple[int, int], size: int):
    if not avatar or not avatar.exists():
        return
    with Image.open(avatar) as source:
        face = ImageOps.fit(source.convert("RGB"), (size, size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    ImageDraw.Draw(card).ellipse((position[0] - 4, position[1] - 4, position[0] + size + 4, position[1] + size + 4),
                                 fill="white")
    card.paste(face, position, mask)


def render_love_card(a: str, b: str, score: int, reading: dict, serial: str, avatar: Path | None = None) -> bytes:
    """星姐姻缘鉴定所's certificate: the two names, the score with a meter, the type, the verdict and the
    reading. `reading` is matchmaker.parse_love's dict."""
    width, pad, inner = 720, 28, 56
    pink, deep, ink, grey = (255, 238, 245), (214, 51, 132), (40, 34, 44), (150, 140, 150)
    title_font, small_font, name_font = _font(44), _font(24), _font(46)
    label_font, score_font, body_font = _font(28), _font(64), _font(30)
    text_width = width - 2 * inner
    scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    names_inline = (scratch.textlength(a, font=name_font) + scratch.textlength(b, font=name_font) + 110) <= text_width
    name_lines = ([] if names_inline else _wrap_cjk(scratch, a, name_font, text_width) + [""]
                  + _wrap_cjk(scratch, b, name_font, text_width))
    verdict = _wrap_cjk(scratch, f"“{reading['verdict']}”", body_font, text_width - 40)
    bullet = scratch.textlength("· ", font=body_font)
    points = [("· " if number == 0 else "", line) for item in reading.get("reading", [])
              for number, line in enumerate(_wrap_cjk(scratch, item, body_font, text_width - bullet))]
    advice = (_wrap_cjk(scratch, f"星姐建议：{reading['advice']}", body_font, text_width)
              if reading.get("advice") else [])
    height = (pad + 40 + 56 + 36 + 30 + (70 if names_inline else 58 * len(name_lines)) + 30 + 40 + 80 + 30 + 50 + 24
              + 30 + 46 * len(verdict) + 40 + 20 + 44 * len(points) + (20 + 44 * len(advice) if advice else 0)
              + 150 + pad)
    card = Image.new("RGB", (width, height), pink)
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((pad, pad, width - pad, height - pad), radius=36, fill="white")
    top = pad + 40

    def centered(text, font, fill, y, stroke=0):
        draw.text(((width - draw.textlength(text, font=font)) / 2, y), text, font=font, fill=fill,
                  stroke_width=stroke, stroke_fill=fill)

    centered("星姐姻缘鉴定所", title_font, deep, top, stroke=1)
    top += 56
    centered(f"鉴定书 No.{serial}", small_font, grey, top)
    top += 36 + 30
    if names_inline:
        a_width, b_width = draw.textlength(a, font=name_font), draw.textlength(b, font=name_font)
        left = (width - (a_width + b_width + 110)) / 2
        draw.text((left, top), a, font=name_font, fill=ink)
        _heart(draw, (int(left + a_width + 55), top + 22), 52, deep)
        draw.text((left + a_width + 110, top), b, font=name_font, fill=ink)
        top += 70
    else:
        for line in name_lines:
            if line:
                centered(line, name_font, ink, top)
            else:
                _heart(draw, (width // 2, top + 18), 44, deep)
            top += 58
    top += 30
    centered("姻缘指数", label_font, grey, top)
    top += 40
    centered(f"{score}%", score_font, deep, top, stroke=1)
    top += 80 + 30
    bar_left, bar_right = inner, width - inner
    draw.rounded_rectangle((bar_left, top, bar_right, top + 26), radius=13, fill=(250, 222, 234))
    if score > 0:
        draw.rounded_rectangle((bar_left, top, bar_left + max(26, (bar_right - bar_left) * score // 100), top + 26),
                               radius=13, fill=deep)
    top += 50
    draw.text((inner, top), f"缘分类型：{reading['kind']}", font=body_font, fill=ink, stroke_width=1, stroke_fill=ink)
    top += 24 + 30
    box_bottom = top + 46 * len(verdict) + 28
    draw.rounded_rectangle((inner - 12, top - 10, width - inner + 12, box_bottom), radius=22, fill=pink)
    for line in verdict:
        draw.text((inner + 8, top + 4), line, font=body_font, fill=deep)
        top += 46
    top = box_bottom + 20 + 20
    for prefix, line in points:
        if prefix:
            draw.text((inner, top), prefix, font=body_font, fill=ink)
        draw.text((inner + bullet, top), line, font=body_font, fill=ink)
        top += 44
    if advice:
        top += 20
        for line in advice:
            draw.text((inner, top), line, font=body_font, fill=ink)
            top += 44
    avatar_size = 96
    footer = height - pad - 30 - avatar_size
    _avatar_disc(card, avatar, (width - inner - avatar_size, footer), avatar_size)
    draw.text((width - inner - avatar_size - 190, footer + 30), "鉴定人：星姐", font=label_font, fill=grey)
    draw.text((inner, height - pad - 50), "本鉴定仅供娱乐 最终解释权归星姐所有", font=small_font, fill=grey)
    output = io.BytesIO()
    card.save(output, "PNG", optimize=True)
    return output.getvalue()


ELEMENT_COLORS = {"金": (196, 146, 26), "木": (46, 139, 87), "水": (30, 110, 200), "火": (215, 55, 45),
                  "土": (150, 100, 50)}


def _png(card: Image.Image) -> bytes:
    output = io.BytesIO()
    card.save(output, "PNG", optimize=True)
    return output.getvalue()


class _Sheet:
    """A white card on a tinted background, laid out top to bottom: lines are measured first, then drawn."""

    def __init__(self, tint, accent, width: int = 720):
        self.width, self.pad, self.inner = width, 28, 56
        self.tint, self.accent = tint, accent
        self.ops, self.height = [], 28 + 40
        self.scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def space(self, amount: int):
        self.height += amount

    def text(self, text: str, size: int, fill=(40, 34, 44), center=False, bold=False, indent=0, line=None):
        font = _font(size)
        step = line or int(size * 1.45)
        for piece in _wrap_cjk(self.scratch, text, font, self.width - 2 * self.inner - indent):
            self.ops.append(("text", self.height, piece, font, fill, center, bold, indent))
            self.height += step

    def box(self, height: int, fill):
        self.ops.append(("box", self.height, height, fill))

    def custom(self, height: int, draw_fn):
        self.ops.append(("custom", self.height, draw_fn))
        self.height += height

    def render(self, avatar: Path | None, signature: str, footnote: str) -> bytes:
        avatar_size = 96
        height = self.height + 30 + avatar_size + 30 + self.pad
        card = Image.new("RGB", (self.width, height), self.tint)
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle((self.pad, self.pad, self.width - self.pad, height - self.pad), radius=36, fill="white")
        for op in self.ops:
            if op[0] == "box":
                _, top, box_height, fill = op
                draw.rounded_rectangle((self.inner - 14, top - 10, self.width - self.inner + 14, top + box_height),
                                       radius=22, fill=fill)
        for op in self.ops:
            if op[0] == "text":
                _, top, piece, font, fill, center, bold, indent = op
                left = (self.width - draw.textlength(piece, font=font)) / 2 if center else self.inner + indent
                draw.text((left, top), piece, font=font, fill=fill, stroke_width=1 if bold else 0, stroke_fill=fill)
            elif op[0] == "custom":
                op[2](card, draw, op[1])
        footer = height - self.pad - 30 - avatar_size
        _avatar_disc(card, avatar, (self.width - self.inner - avatar_size, footer), avatar_size)
        label = _font(28)
        draw.text((self.width - self.inner - avatar_size - 20 - draw.textlength(signature, font=label), footer + 30),
                  signature, font=label, fill=(150, 140, 150))
        draw.text((self.inner, height - self.pad - 50), footnote, font=_font(24), fill=(150, 140, 150))
        return _png(card)


def render_bazi_card(asker: str, facts: dict, reading: dict, avatar: Path | None = None) -> bytes:
    """星姐算命馆's chart: the four pillars coloured by 五行, the 五行 count, 日主 and 大运, then the reading.
    `facts` is fortune.bazi_facts, `reading` fortune.parse_reading with BAZI_FIELDS."""
    purple, grey, ink = (110, 70, 200), (150, 140, 150), (40, 34, 44)
    sheet = _Sheet((241, 236, 255), purple)
    sheet.text("星姐算命馆", 44, purple, center=True, bold=True)
    sheet.text("八字命盘 · 仅供娱乐", 24, grey, center=True)
    sheet.space(16)
    sheet.text(f"{asker} 的命盘", 34, ink, center=True)
    sheet.text(f"阳历 {facts['solar']}", 24, grey, center=True, line=34)
    sheet.text(f"农历 {facts['lunar']} · 属{facts['zodiac']} · {facts['star']}", 24, grey, center=True, line=34)
    sheet.space(20)
    pillars = facts["pillars"]

    def draw_pillars(card, draw, top):
        column = (sheet.width - 2 * sheet.inner) / len(pillars)
        for index, pillar in enumerate(pillars):
            middle = sheet.inner + column * index + column / 2
            rows = [(pillar["name"], _font(24), grey, 0), (pillar["shishen"], _font(24), purple, 34),
                    (pillar["ganzhi"][0], _font(60), ELEMENT_COLORS.get(pillar["wuxing"][0], ink), 70),
                    (pillar["ganzhi"][1], _font(60), ELEMENT_COLORS.get(pillar["wuxing"][1], ink), 146),
                    (pillar["nayin"], _font(22), grey, 222)]
            for text, font, fill, offset in rows:
                draw.text((middle - draw.textlength(text, font=font) / 2, top + offset), text, font=font, fill=fill)

    sheet.custom(262, draw_pillars)

    def draw_elements(card, draw, top):
        chip = (sheet.width - 2 * sheet.inner) / 5
        for index, element in enumerate("金木水火土"):
            left = sheet.inner + chip * index + 8
            color = ELEMENT_COLORS[element]
            count = facts["counts"][element]
            draw.rounded_rectangle((left, top, left + chip - 16, top + 52), radius=26,
                                   fill=color if count else (238, 234, 242))
            text = f"{element} {count}"
            font = _font(28)
            draw.text((left + (chip - 16 - draw.textlength(text, font=font)) / 2, top + 9), text, font=font,
                      fill="white" if count else grey)

    sheet.custom(70, draw_elements)
    missing = "、".join(facts["missing"])
    start = f" · {facts['luck']['start']}" if facts.get("luck") else ""
    sheet.text(f"日主 {facts['day_master']} · {'五行缺' + missing if missing else '五行齐全'}{start}", 28, ink,
               center=True)
    if facts.get("luck"):
        sheet.text("大运 " + " ".join(facts["luck"]["steps"]), 22, grey, center=True, line=34)
    sheet.space(26)
    summary_top = sheet.height
    summary_lines = len(_wrap_cjk(sheet.scratch, f"“{reading['summary']}”", _font(32), sheet.width - 2 * sheet.inner))
    sheet.box(summary_lines * 46 + 16, (241, 236, 255))
    sheet.height = summary_top + 6
    sheet.text(f"“{reading['summary']}”", 32, purple, center=True, line=46)
    sheet.space(26)
    for label, key in (("性格", "personality"), ("学业事业", "career"), ("感情", "love"), ("财运", "wealth"),
                       ("今年运势", "year")):
        if reading.get(key):
            sheet.text(label, 26, purple, bold=True, line=38)
            sheet.text(reading[key], 28, ink, indent=16, line=42)
            sheet.space(10)
    if reading.get("advice"):
        sheet.space(6)
        sheet.text(f"星姐建议：{reading['advice']}", 28, ink, line=42)
    return sheet.render(avatar, "批命人：星姐", "命运握在自己手里 本命盘仅供娱乐")


def render_fortune_card(asker: str, draw_result: dict, reading: dict, day: dict, avatar: Path | None = None) -> bytes:
    """星姐神社's lot of the day: the level, the verse, its meaning, the real 黄历 宜/忌 and the lucky charms.
    `draw_result` is fortune.daily_draw, `day` fortune.almanac, `reading` parse_reading with DRAW_FIELDS."""
    crimson, grey, ink = (200, 40, 50), (150, 140, 150), (40, 34, 44)
    good = draw_result["level"] not in ("凶", "大凶")
    sheet = _Sheet((255, 242, 232), crimson)
    sheet.text("星姐神社", 44, crimson, center=True, bold=True)
    sheet.text(f"今日运势 · {day['solar']} · {day['lunar'].removeprefix('农历')}", 22, grey, center=True)
    sheet.space(12)
    sheet.text(asker, 30, ink, center=True)

    def draw_level(card, draw, top):
        size = 170
        left = (sheet.width - size) / 2
        color = crimson if good else (90, 90, 110)
        draw.ellipse((left, top, left + size, top + size), outline=color, width=6)
        font = _font(64 if len(draw_result["level"]) > 1 else 84)
        text = draw_result["level"]
        draw.text(((sheet.width - draw.textlength(text, font=font)) / 2, top + (size - font.size) / 2 - 6), text,
                  font=font, fill=color, stroke_width=1, stroke_fill=color)

    sheet.space(10)
    sheet.custom(196, draw_level)
    for verse in re.split(r"[，,。；;\s]+", reading["poem"]):
        if verse:
            sheet.text(verse, 34, ink, center=True, line=50)
    sheet.space(14)
    sheet.text(reading["meaning"], 28, ink, line=42)
    sheet.space(20)

    def draw_yi_ji(card, draw, top):
        half = (sheet.width - 2 * sheet.inner - 20) / 2
        for index, (label, items, fill, color) in enumerate((("宜", day["yi"][:4], (232, 246, 236), (46, 139, 87)),
                                                             ("忌", day["ji"][:4], (252, 234, 234), crimson))):
            left = sheet.inner + index * (half + 20)
            draw.rounded_rectangle((left, top, left + half, top + 170), radius=22, fill=fill)
            draw.text((left + 20, top + 14), label, font=_font(34), fill=color, stroke_width=1, stroke_fill=color)
            for row, item in enumerate(items):
                draw.text((left + 74, top + 18 + row * 37), item, font=_font(26), fill=ink)

    sheet.custom(190, draw_yi_ji)
    sheet.text(f"幸运色 {draw_result['color']}　幸运数字 {draw_result['number']}", 28, ink, center=True, line=44)
    if reading.get("advice"):
        sheet.text(f"星姐建议：{reading['advice']}", 28, ink, line=42)
    return sheet.render(avatar, "巫女：星姐", "宜忌来自今天的黄历 每人每天一签")


def render_eq_card(low: str, high: str, avatar: Path | None = None) -> bytes:
    width, pad, gap = 720, 36, 24
    label_font, body_font, sign_font = _font(34), _font(40), _font(26)
    scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    avatar_size = 150
    rows = [("低情商", low, (120, 124, 132), (242, 243, 245), width - 4 * pad),
            ("高情商", high, (108, 76, 230), (240, 235, 255), width - 4 * pad - avatar_size + 20)]
    layout = []
    for label, text, ink, fill, text_width in rows:
        lines = _wrap(scratch, text, body_font, text_width)
        layout.append((label, lines, ink, fill, 34 + 18 + len(lines) * 54 + 2 * pad // 2 + 20))
    height = pad + sum(row[4] for row in layout) + gap * (len(layout) - 1) + pad + 40
    card = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(card)
    top = pad
    for label, lines, ink, fill, box_height in layout:
        draw.rounded_rectangle((pad, top, width - pad, top + box_height), radius=28, fill=fill)
        draw.text((2 * pad, top + 22), label, font=label_font, fill=ink, stroke_width=1, stroke_fill=ink)
        for index, line in enumerate(lines):
            draw.text((2 * pad, top + 22 + 34 + 18 + index * 54), line, font=body_font, fill=(34, 34, 40))
        top += box_height + gap
    draw.text((width - pad - 150, height - pad - 30), "—— 星姐", font=sign_font, fill=(150, 150, 160))
    if avatar and avatar.exists():
        with Image.open(avatar) as source:
            face = ImageOps.fit(source.convert("RGB"), (avatar_size, avatar_size))
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        box_top = top - gap - layout[-1][4]
        position = (width - pad - avatar_size - 16, box_top + (layout[-1][4] - avatar_size) // 2)
        draw.ellipse((position[0] - 5, position[1] - 5, position[0] + avatar_size + 5, position[1] + avatar_size + 5),
                     fill="white")
        card.paste(face, position, mask)
    output = io.BytesIO()
    card.save(output, "PNG", optimize=True)
    return output.getvalue()
