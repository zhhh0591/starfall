"""Build the candidate pool of real human cue -> reply pairs (no model calls; the bot judges them later).

Sources (see README): LCCC-base (thu-coai/CDial-GPT, MIT; Weibo conversations) and CN-SarcasmBench
(Devon018, CC-BY-NC-4.0; real Bilibili sarcastic replies). Raw files live in corpus/raw_*/ and are
treated as untrusted data: they are only parsed, never executed.

    python -I build_human_corpus.py
"""
from collections import Counter
import gzip
import json
from pathlib import Path
import random
import re
import sys
import zlib

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from guardian import CRUDE, is_injection  # noqa: E402

RAW_LCCC = (ROOT / "corpus/raw_lccc/lccc_base_test.jsonl.gz", ROOT / "corpus/raw_lccc/lccc_base_train.part.gz")
RAW_SARCASM = ROOT / "corpus/raw_sarcasm/CN-SarcasmBench.json"
OUT = ROOT / "corpus/human_candidates.jsonl"
SENSITIVE = re.compile(
    r"政府|政治|共产|中共|国民党|领导人|主席|总理|总统|习|毛泽东|台独|藏独|疆独|港独|法轮|六四|游行|示威|川普|特朗普|拜登|"
    r"美帝|日本鬼子|小日本|棒子|黑鬼|黑人|穆斯林|回民|同性恋|基佬|女权|男权|田园|拳师|普信|小仙女|直男癌|"
    r"约炮|做爱|性交|鸡巴|奶子|裸|色情|黄片|AV|av|开房|处女|强奸|毒品|自杀|去死|杀了|弄死|砍死|"
    r"微信|加我|QQ群|qq群|代购|淘宝|店铺|链接|优惠|红包|转发|关注我|互粉|抽奖")
LOW_INFO = re.compile(r"^(哈+|嗯+|恩+|好的?|好吧|是的|是啊|对啊|对的|顶+|\+1|谢谢|谢了|收到|哦+|噢+|啊+|呵呵|[\W\d_]+)$")
WIT = re.compile(
    r"[？?]$|合着|怕不是|建议|那你|鉴定为|你是懂|难道|不会吧|原来|敢情|好家伙|照你这么说|这么说|还能|就这|所以说|"
    r"你怎么知道|我信了|说得好像|不愧是|你行你上|赢麻了|拿捏|破防|绷不住|笑死|反正|毕竟|果然|没想到|至少|起码|"
    r"那我|我就|你先|先把|别说|不如|难怪|怪不得|只能|居然|竟然|万一|要不|然后呢|厉害了|服了|可以的|有道理|真相|"
    r"重点是|问题是|谁让|怪我|托你|多亏|幸亏|好在|还好|也就|顶多|大概|可能是|应该是|估计")
PROVOKE = re.compile(
    r"吹|就这|急了|你行你上|智商|丑|菜|垃圾|废物|蠢|笨|傻|脑子|闭嘴|装|恶心|有病|神经|搞笑|可笑|呵呵|不配|"
    r"算老几|穷|矮|胖|low|小学生|键盘侠|喷子|滚|讨厌|烦人|没用|不行|差劲|弱")


def clean(text: str) -> str:
    text = re.sub(r"回复\s*@[^:：]{1,20}[:：]", "", text)
    text = re.sub(r"https?://\S+|www\.\S+|@\S{1,20}|\b(?:av|BV)\w+", "", text)
    text = re.sub(r"\[[^\[\]]{1,10}\]", "", text)  # bilibili emote codes such as [doge]
    text = re.sub(r"哈{4,}", "哈哈哈", text)
    text = re.sub(r"[~～]{2,}", "~", text)
    return re.sub(r"\s+", " ", text).strip()


def lccc_dialogues():
    for path in RAW_LCCC:
        if not path.exists():
            continue
        stream = zlib.decompressobj(16 + zlib.MAX_WBITS)
        buffer = b""
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1 << 20)
                if not chunk:
                    break
                try:
                    buffer += stream.decompress(chunk)
                except zlib.error:
                    break  # the train file is a truncated download; keep the complete lines we have
                *lines, buffer = buffer.split(b"\n")
                for line in lines:
                    try:
                        turns = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(turns, list):
                        yield [re.sub(r"(?<=\S) (?=\S)", "", str(turn)) for turn in turns]


def sarcasm_pairs():
    if not RAW_SARCASM.exists():
        return
    for thread in json.loads(RAW_SARCASM.read_text(encoding="utf-8")):
        comments = thread.get("comments") or []
        if len(comments) >= 2:
            yield comments[0], comments[-1], thread.get("classification", "")


def acceptable(cue: str, reply: str, comeback: bool) -> bool:
    if not (4 <= len(cue) <= 40 and 4 <= len(reply) <= 25) or LOW_INFO.match(reply):
        return False
    if CRUDE.search(reply) or SENSITIVE.search(reply) or SENSITIVE.search(cue) or is_injection(cue + reply):
        return False
    if not comeback and CRUDE.search(cue):
        return False
    return not re.search(r"[a-zA-Z]{6,}|\d{5,}", cue + reply)


def main():
    random.seed(20261027)
    seen, per_reply, rows = set(), Counter(), []
    for turns in lccc_dialogues():
        for cue, reply in zip(turns, turns[1:]):
            cue, reply = clean(cue), clean(reply)
            comeback = bool(PROVOKE.search(cue))
            if not acceptable(cue, reply, comeback) or (cue, reply) in seen or per_reply[reply] >= 3:
                continue
            markers = len(WIT.findall(reply))
            if not markers and random.random() > 0.03:
                continue  # keep a small random share of plain replies so the judge sees variety
            seen.add((cue, reply))
            per_reply[reply] += 1
            rows.append({"pool": "comeback" if comeback else "banter", "cue": cue, "reply": reply,
                         "src": "lccc", "pre": markers + random.random()})
    sarcastic = 0
    for cue, reply, kind in sarcasm_pairs():
        cue, reply = clean(cue), clean(reply)
        if acceptable(cue[:40], reply, True) and (cue, reply) not in seen:
            seen.add((cue, reply))
            rows.append({"pool": "comeback", "cue": cue[:40], "reply": reply, "src": "sarcasm",
                         "kind": kind, "pre": 5 + random.random()})
            sarcastic += 1
    limits = {"banter": 40000, "comeback": 12000}
    kept = []
    for pool, limit in limits.items():
        pool_rows = sorted((row for row in rows if row["pool"] == pool), key=lambda row: row["pre"], reverse=True)
        kept += pool_rows[:limit]
    random.shuffle(kept)
    with OUT.open("w", encoding="utf-8") as output:
        for index, row in enumerate(kept):
            row["id"] = index
            row["pre"] = round(row["pre"], 2)
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts = Counter(row["pool"] for row in kept)
    print(f"候选 {len(kept)} 组（日常接梗 {counts['banter']}，怼回去 {counts['comeback']}，其中B站阴阳 {sarcastic}）")


if __name__ == "__main__":
    main()
