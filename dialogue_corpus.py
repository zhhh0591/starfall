"""Retrieve topic-matched dialogue examples without treating them as instructions."""
from collections import defaultdict
import json
from pathlib import Path
import random
import re

import jieba

ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT / "corpus/dialogue_pairs.jsonl"
STOP = {"什么", "怎么", "可以", "觉得", "这个", "那个", "我们", "你们", "他们", "还是",
        "一个", "一下", "一下子", "就是", "然后", "现在", "最近", "真的", "不是", "因为"}
STOP |= {"今天", "昨天", "明天", "太多", "麻烦", "感觉", "好像", "有点", "事情", "问题", "时候"}


def terms(text: str) -> set[str]:
    return {word.lower() for word in jieba.lcut(text) if len(word.strip()) >= 2 and word not in STOP}


class DialogueCorpus:
    def __init__(self, path: Path = CORPUS_PATH):
        self.rows = []
        self.index = defaultdict(list)
        self.recent = []
        if not path.exists():
            return
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                    if not all(isinstance(row.get(k), str) for k in ("topic", "cue", "reply")):
                        continue
                    idx = len(self.rows)
                    self.rows.append(row)
                    for word in terms(row["topic"] + " " + row["cue"]):
                        self.index[word].append(idx)
                except (ValueError, TypeError):
                    continue

    def retrieve(self, message: str, count: int = 6) -> list[dict]:
        words = terms(message)
        if not words or not self.rows or count <= 0:
            return []
        scores = defaultdict(float)
        for word in words:
            hits = self.index.get(word, [])
            if len(hits) > max(700, len(self.rows) // 8):
                continue
            for idx in hits:
                row = self.rows[idx]
                scores[idx] += (2 if word in row["topic"] else 0) + (2 if word in row["cue"] else 0)
        if not scores:
            return []
        candidates = [idx for idx, score in scores.items() if score >= 3 and idx not in self.recent]
        candidates.sort(key=lambda idx: (scores[idx], random.random()), reverse=True)
        selected = []
        topics = set()
        for idx in candidates:
            if self.rows[idx]["topic"] in topics:
                continue
            selected.append(idx)
            topics.add(self.rows[idx]["topic"])
            if len(selected) >= count:
                break
        self.recent = (self.recent + selected)[-100:]
        return [self.rows[idx] for idx in selected]
