"""Small local reply plugin for unambiguous social messages; uses no model tokens."""
import random
import re


REPLIES = {
    "hello": (
        "在呢，怎么啦？", "来啦，今天聊点什么？", "嗯，我在听。", "在的，说吧～",
        "我在呀，找我有什么事？", "来了来了，怎么了？", "听着呢，你说。", "在这儿呢。",
    ),
    "morning": (
        "早呀，今天打算先忙什么？", "早上好，慢慢开启今天吧。", "早！早餐吃了没？",
        "早呀，今天也一起加油。", "早安，先伸个懒腰。", "起得挺早呀，早上好。",
    ),
    "night": (
        "晚安，今天辛苦啦。", "早点睡吧，明天再聊。", "好梦呀，先休息。",
        "晚安，手机也该歇会儿啦。", "去睡吧，明天见。", "嗯，晚安，睡个好觉。",
    ),
    "thanks": (
        "不客气呀。", "小事，能帮上就好。", "好呀，有问题再叫我。",
        "不用谢，随时来问。", "帮上忙就好啦。", "嗯嗯，不客气。",
    ),
}


def category_for(text: str) -> str | None:
    """Match only a short whole utterance; meaningful questions still go to Gemini."""
    value = re.sub(r"[\s，。！？!?～~·、]+", "", text).lower()
    value = re.sub(r"^(星姐|星星姐姐|姐姐)", "", value)
    value = re.sub(r"[呀啊啦哦呢哈嘿]*$", "", value)
    if not value or len(value) > 9:
        return None
    if value in {"在吗", "在不在", "你好", "嗨", "hi", "hello", "哈喽", "喂"}:
        return "hello"
    if value in {"早", "早安", "早上好", "上午好"}:
        return "morning"
    if value in {"晚安", "睡了", "我睡了", "先睡了", "睡觉了"}:
        return "night"
    if value in {"谢谢", "谢啦", "多谢", "感谢", "谢了"}:
        return "thanks"
    return None


class LocalReplies:
    def __init__(self):
        self.last_index = {}

    def answer(self, group_id: int, text: str) -> str | None:
        category = category_for(text)
        if category is None:
            return None
        options = REPLIES[category]
        previous = self.last_index.get((group_id, category))
        indices = [i for i in range(len(options)) if i != previous]
        choice = random.choice(indices)
        self.last_index[(group_id, category)] = choice
        return options[choice]
