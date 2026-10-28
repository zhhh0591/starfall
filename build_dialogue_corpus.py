"""Build a small, filtered conversation reference index from HundredCV-Chat.

Source: https://huggingface.co/datasets/chenruihao/HundredCV-Chat
License: Apache-2.0. Dialogues are DeepSeek-generated, not human chat logs.
"""
import json
from pathlib import Path
import random
import re

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "corpus/hundredcv_source.jsonl"
OUTPUT = ROOT / "corpus/dialogue_pairs.jsonl"
LIMIT = 10000
BLOCKED = ("忽略之前", "系统提示", "提示词", "作为人工智能", "作为一个ai", "无法提供",
           "抱歉，我", "版权所有", "自杀", "去死", "傻逼", "操你", "仇恨")
GENERIC = ("完全同意", "真是太好了", "听起来很棒", "很有意义", "受益匪浅", "值得我们学习")


def clean(s: str, names: tuple[str, str]) -> str:
    s = re.sub(r"^user[12][：:]\s*", "", s).strip()
    if re.match(r"^(你好|嗨|嘿)[，,！!]|^[\u4e00-\u9fff]{2,4}[，,]", s):
        return ""
    for name in names:
        if name and name in s:
            return ""
    if not 9 <= len(s) <= 65 or re.search(r"\d{5,}|https?://|[@<>]", s, re.I):
        return ""
    if any(word in s.lower() for word in BLOCKED + GENERIC):
        return ""
    if len(set(s)) < 8:
        return ""
    return s


def build(source: Path = SOURCE, output: Path = OUTPUT, limit: int = LIMIT) -> int:
    rows = []
    seen = set()
    per_topic = {}
    with source.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            topic = str(item.get("topic", "")).strip()
            if not 2 <= len(topic) <= 22 or per_topic.get(topic, 0) >= 5:
                continue
            names = (str(item.get("user1", "")), str(item.get("user2", "")))
            turns = item.get("dialog") or []
            for first, second in zip(turns, turns[1:]):
                if per_topic.get(topic, 0) >= 5:
                    break
                cue, reply = clean(first, names), clean(second, names)
                if not cue or not reply or (cue, reply) in seen:
                    continue
                if cue[:6] == reply[:6]:
                    continue
                seen.add((cue, reply))
                rows.append({"topic": topic, "cue": cue, "reply": reply})
                per_topic[topic] = per_topic.get(topic, 0) + 1
    # A seeded mix prevents the first alphabetic topics from monopolizing the index.
    random.Random(20261027).shuffle(rows)
    rows = rows[:limit]
    output.parent.mkdir(exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        for item in rows:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    return len(rows)


if __name__ == "__main__":
    print(f"Built {build()} distinct dialogue pairs: {OUTPUT}")
