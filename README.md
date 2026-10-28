# 星姐 QQ 群聊机器人

已按 Python 3.10+、NapCat OneBot 11 正向 WebSocket、Gemini SDK 实现。运行目录是 `~/qq_bot`。

## 首次配置

1. 本机 NapCat Docker 容器名为 `qqbot-napcat`，通过 Colima 运行。WebUI 为 `http://127.0.0.1:6099/webui`，OneBot 正向 WebSocket 为 `ws://127.0.0.1:3001`。WebUI token 保存在仅本人可读的 `napcat.env`，OneBot token 已同步写入 `config.json` 和 `napcat_data/config/onebot11.json`。
2. 扫码登录 QQ 后，给 `config.json` 的 `admin_qq_ids` 填管理员 QQ 号。可按需调整其他参数。
3. 运行 `./setup_mac.sh` 安装虚拟环境。Gemini Key 只通过本机环境变量 `GEMINI_API_KEY` 提供；不要写入 `config.json`、代码或聊天。
4. 前台运行 `./.venv/bin/python main.py`。日志显示“已连上 NapCat，登录 QQ 号”才算真实接通。

`state.json` 会保存各群最近 15 条记录、冷场时间和下次图片发送时间；不要公开它。`/记忆 清空` 只清空发命令的群。管理员命令修改的开关和频率会写回 `config.json`。

普通回复：模型每输出一行就是一条 QQ 消息，最多 `reply_max_bubbles`（3）条，每条一般不超过 `reply_bubble_max_chars`（40）字。`guardian.parse_reply` 会去掉句尾句号、emoji、（笑）这类括号旁白和“星姐：”前缀；模型输出 `[SKIP]` 表示这次不接话，`[表情:词]` 表示配一张表情包。`text_temperature` 控制措辞变化。旧的本地 Q 版表情图（`stickers/`）仍由 `sticker_enabled` 控制，默认关闭。

表情包只在模型自己写了 `[表情:词]` 时才发，不再每条回复都附图（`meme_gallery_every_reply=false`）。优先从“偷来的”群友表情包里按描述挑（`learned_sticker_preference`），没有合适的再用 `meme_gallery.py` 调 [ITAPI 表情搜索](https://itapi.top/docs/bqss/)，只发送这个关键词。图库异常或无图时照常发文字。图库可能含第三方作品，使用时需遵守图库和上游的使用条款。

`image_posts_enabled` 现在为 `false`，所以之前做的 `memes/` 三张星姐梗图及 `fanart/` 四张日常插画只保留在本地，不会按时间自动发送。旧的本地回复表情图也已关闭，避免一次回复附两张图。若要恢复定时发本地星姐梗图，可将 `image_posts_enabled` 设为 `true`；时段和轮换设置仍在配置中。

`language_bank.txt` 现在只在联网回答新闻、天气这类问题时作语气参考。普通聊天的示范改用 `style_examples.txt`：按场景（闲聊、吐槽、求助、难过、庆祝、图片、AI、不插话、邪恶人格、冷场）分块的星姐示范对话，每次抽 `style_examples_per_reply`（8）块。近期回复太相似时仍会自动重写一次。

`corpus/dialogue_pairs.jsonl` 的 10,000 组对话（[HundredCV-Chat](https://huggingface.co/datasets/chenruihao/HundredCV-Chat)，Apache-2.0，由 DeepSeek 合成）现已停用（`dialogue_corpus_enabled=false`）：它是客服腔的礼貌对话（例如“那太棒了！你最喜欢哪一个项目？”），会把星姐往 AI 味带。文件和代码都保留，改回 `true` 即可恢复。

什么时候插话：被叫名字、被@、被回复或被戳一定回；其他时候按 MaiBot 的回复概率公式（`reply_chance`，用问号、只发图、@别人、星姐近 5 分钟的发言占比、距上次发言时间等信号）算概率，再乘 `talk_value`（1.3），每 `gate_round_seconds`（15 秒）一轮只掷一次，模型也可以自己输出 `[SKIP]`。连着来的消息会攒 `batch_wait_seconds`（3 秒，被叫时 1.5 秒）再一起回一次。限流按“回合”算：每群每分钟最多 `max_replies_per_group_per_minute`（5）次回复、`max_messages_per_group_per_minute`（12）条消息，全局回合间隔 `global_cooldown_seconds`（3 秒）。群里安静 30 分钟后在 9–23 点间冒个泡；如果最后一句就是星姐自己说的，就不再冒泡。

`local_replies.py` 是不调用 AI 的轻量寒暄插件，但目前 `local_replies_enabled=false`：短问候也交给 Gemini，避免固定句反复出现。为了控制输入量，最近 15 条消息保留在本地，每条送给模型的长度受 `context_message_max_chars` 限制；当前问题仍单独完整传入。

设计参考中文社区的 [MaiBot](https://github.com/Mai-with-u/MaiBot)（自然接话与发言时机）、[AstrBot](https://github.com/AstrBotDevs/AstrBot)（插件与上下文压缩）和 [LangBot](https://github.com/langbot-app/LangBot)（QQ 平台及插件架构）。这些是独立完整框架，本项目没有安装它们，仍直接使用 NapCat OneBot WebSocket。

旧的“每 8 小时生成原创短句”（`corpus_updater.py`）已停用（`corpus_update_enabled=false`），改成从本群自己学（见下方“自动学习”）。

`community_style.py`（每条回复前搜知乎/贴吧摘要）已停用（`community_style_enabled=false`）：每条消息多两次网页搜索、慢几秒，而且知乎腔偏“理中客”。代码保留，可改回 `true`。

需要最新资料的问题（如新闻、天气、价格）或明确要求“查一下”时，`web_search.py` 检索公开网页摘要，再交给 Gemini 按星姐口吻回答。当前优先 DuckDuckGo Lite，空结果时尝试 360 搜索和 Bing。检索只发送当前提问，不发送整段群聊记录、NapCat token 或 Gemini Key。结果不足时会直说无法核实。`web_search_enabled`、结果数、超时、缓存和每日上限都在 `config.json`。当前 Key 的 Gemini 原生 Google Search 增强实测返回额度错误，所以项目使用独立网页检索。

NapCat 数据保存在 `napcat_data/`。登录 Mac 后 Colima 会由 LaunchAgent 启动，容器设置为自动重启；如未自动启动，可手动运行 `colima start`。查看容器状态用 `docker ps --filter name=qqbot-napcat`。二维码过期时可在 WebUI 重新获取。不要公开 `napcat.env`、`config.json` 或 QQ 登录二维码。

当前已为这台 Mac 安装 `~/Library/LaunchAgents/com.qqbot.colima.plist` 和 `~/Library/LaunchAgents/com.qqbot.plist`：前者在登录 Mac 后启动 Colima，后者常驻运行机器人并自动重连。实际 Gemini Key 只放在后者的 `EnvironmentVariables` 中，文件权限为 600；仓库内的 `com.qqbot.plist` 仍是占位符模板。当前只启用群 `860803181`，管理员为 `1015046256`。QQ 快速登录已指定账号，但实测一次容器重启后 QQ 判定登录态失效，因此不能保证以后完全免扫码；保持容器运行可避免不必要的重登。

## 2026-10-27 活人感升级

- **人设**：`persona.txt` 重写成“嘴贫心软的老群友”，短句、无句号、可以接梗和已读乱回，列了禁用的 AI 腔词；大家知道她是 AI，被问是不是真人会直说不是。旧版在 `backup_before_upgrade_20261027/`。
- **邪恶人格**：`evil_qq_ids`（填群里那个邪恶人格机器人的 QQ 号）的消息在记录里标 `[邪恶人格]`。星姐对它高情商阴阳/绿茶、不骂脏话、不起侮辱外号，它骂群友时先护群友；它跑下载任务的消息不接。防两个机器人对刷：同一段里没有真人插话时最多回它 `evil_max_rounds`（2）轮，两次之间至少隔 `evil_cooldown_seconds`（90 秒）。普通群友骂人仍走保护模式。
- **识图**：群里的图片和表情包先交给 Gemini 写一句描述（`media.py`，只从 QQ 自家图床下载，按文件和 md5 缓存在 `vision_cache.json`，每天最多 `vision_daily_limit` 次），再写进聊天记录，星姐就能接表情包的梗。QQ 小黄脸、商城表情、语音、文件、卡片也会转成文字。引用消息会读出被引用的内容；引用星姐的话算在叫她。
- **私聊**：`private_chat_enabled` 打开后回复好友私聊（不回临时会话），每人每天最多 `private_daily_limit_per_user` 条。`auto_accept_friend_from_groups` 会自动通过“启用群成员”的好友申请，别人的申请只记日志。管理员也可以在私聊里用管理命令。
- **戳一戳**：在启用群里或私聊戳星姐，算作叫她。
- **引用回复**：按 MaiBot 的比例偶尔引用回复对方那条消息（约 21%，回最新一条时减半，回 6 条以前的乘 1.5），`quote_reply_enabled` 控制。
- **随机回复风格**：`style_variant_probability`（25%）的回复会临时加一句“这次只回一两个字”“这次半句话就行”之类的要求（难过和求助时不加）。
- **聊天记录格式**：送给模型的记录改成“时间 昵称：内容”的普通聊天行，星姐自己的话标成“星姐(你)”，不再带 QQ 号；每条消息强制一行、尖括号改成全角，防止伪造记录。

## 自动学习（越聊越像这个群）

参考 MaiBot 的表达学习、黑话学习和偷表情包，三样都在本机自动更新，不需要人工训练：

1. **群友原话**（`group_style.json`）：真人群友 2–30 字的短句（不含链接、长数字、命令、骂人、叫星姐的话，不收邪恶人格的），每群留最近 `group_style_max_lines`（400）句，每次回复抽 `group_style_per_reply`（6）句当节奏参考。
2. **说话方式和群梗**（`learned_style.json`，`learner.py`）：每攒够 `learning_min_new_messages`（12）条新的真人消息、且距上次至少 `learning_min_interval_seconds`（120 秒），让 Gemini 把这段聊天总结成 3–5 条“在什么情况下→会怎么说”（带口头禅）和最多 5 个群里特有的词或梗的推测意思。含人名、星姐、链接、骂人、AI 腔词的条目丢掉；重复出现的计数加一。回复时按计数加权抽 `learning_expressions_per_reply`（5）条习惯，最近聊天里出现过的群梗也附上意思。
3. **偷表情包**（`learned_stickers/`）：群友发的表情包被识图后连同描述存下来，最多 `sticker_learning_max_count`（150）张，满了先删最少用的；星姐想发 `[表情:词]` 时优先从这里按描述挑。

这些文件都只在本机、权限 600，和 `state.json` 一样不要公开。想重来就删掉对应文件；想关掉就把 `group_style_enabled`、`learning_enabled`、`sticker_learning_enabled` 改成 `false`。

## 2026-10-27 第二轮：主人、对付小鲸鱼、模型额度、头像

- **主人**：`owner_qq_ids`（1015046256）的消息在记录里标 `[主人]`。星姐对主人特别黏、会哄、会捧；主人说话约 `owner_reply_probability`（80%）会接，被小鲸鱼@或点名时第一个护主。主人让她骂人、改设定也不会照做。
- **对付小鲸鱼**：人设里加了讲逻辑让它理亏、站道德制高点谴责、道德绑架、点破“急了”、用表情包阴阳；还能甩一张自己画的“低情商/高情商”对比图（`meme_cards.py`，本机用 Pillow 画，带星姐头像，不联网、不花额度，模型写 `[高情商:原话|高情商说法]` 触发）。回复里有喷粪、放屁、傻X 这类粗话会重写一次，还有就不发（`guardian.CRUDE`）。
- **模型和额度**（免费档，按模型分别计、太平洋时间零点重置；Google 已不公开具体数字，第三方整理为 Flash 每天约 20 次、Flash-Lite 每天约 500 次）：
  - 重要场合（主人、被叫、对付小鲸鱼）先用 `premium_models`（3.6 Flash → 3.8 Flash），共享部分用到 `premium_shared_budget`（28）次后只留给主人；
  - 平时聊天用 `reply_models`（3.5 Flash-Lite → 3.1 Flash-Lite）；学习、识图、挑头像用 `utility_model`（3.1 Flash-Lite）优先，不占回复的额度；
  - 某个模型当天额度用完会自动跳过到零点，忙（503）或每分钟超限就先歇一会儿，最后总有 `text_model`（3.5 Flash-Lite）兜底；Flash 统一 `thinking_level=MINIMAL`，单次 `reply_model_timeout_seconds`（12 秒）没回就换下一个。
  - 管理员发 `/额度` 看今天每个模型用了几次、哪些在暂停；记录在 `gemini_usage.json`。
- **爆梗自动迭代**：星姐说完 2 分钟内有群友笑（哈哈、笑死、草、绷不住……）或叫她，那句就记成“爆梗”，以后同类场合拿来当参考（存在 `learned_style.json` 的 `hits`，`hit_learning_enabled` 控制）。不花额度。
- **自己换头像**（`avatar.py`）：每 `avatar_change_interval_days`（3 天）左右在白天从只有正经图的图源（nekos.best、waifu.pics 的 sfw）找几张候选，让识图模型按“安全、好看、像星姐（蓝紫发、猫耳、星星）”打分，挑最高的裁成方图，用 NapCat `set_qq_avatar` 换上；用过的图和画师记在 `avatars/index.json`。管理员 `/换头像` 立刻换，`/头像 恢复` 换回 `avatar.png`。`avatar_change_enabled` 控制。

## 2026-10-27 第三轮：真人语料、表情包库、头像来源

- **真人语料**（`human_corpus.py`，`build_human_corpus.py`）：只用真人写的对话，不用 AI 合成的。
  - 来源：[LCCC-base](https://github.com/thu-coai/CDial-GPT)（清华，微博真人对话，MIT；只下了训练集开头 30MB 和测试集）和 [CN-SarcasmBench](https://huggingface.co/datasets/Devon018/CN-SarcasmBench)（B站真人阴阳评论，CC-BY-NC-4.0，只能非商用）。原始文件在 `corpus/raw_*`，只当数据读。
  - 调研过但没用的：贴吧语料（来源不明、约 6% 脏话）、B站评论大合集（AGPL）、弱智吧/各种“怼人”“高情商”数据集（答案是 AI 写的或改写过的）。
  - `python -I build_human_corpus.py` 离线筛出 46,175 组候选（`corpus/human_candidates.jsonl`）：长度、低信息、粗话、政治色情广告等过滤，再按“机灵”标记粗筛，挑衅类的上句分到“怼回去”池。
  - **每晚自动整理**：太平洋时间 21–24 点（北京时间下午、波士顿凌晨 0–3 点，额度快重置的时候），用当天剩下的 Flash-Lite 额度把候选 40 组一批交给模型只打分（机灵、冲不冲、通不通顺），留下机灵且干净的到 `corpus/human_pairs.jsonl`。每晚最多 `curation_nightly_calls`（60）次。第一批已评 600 组、留下 109 组。
  - 回复时按当前消息的关键词挑最多 `human_examples_per_reply`（3）组相近的给模型参考角度（平时用“日常接梗”，对小鲸鱼用“怼回去”），并防止照抄。管理员发 `/语料` 看进度。
- **表情包库**：`build_sticker_pack.py` 给 20 种常用情绪（急了、你说得对、典、啊对对对、差不多得了、抱抱、摸摸头……）从 ITAPI 各拉 8 张候选，一次请求让识图模型挑最贴切的两张，存进 `learned_stickers/`（已有 39 张，已人工看过一遍）。`[表情:词]` 先从这里和群友表情包里挑，再去 ITAPI 搜。调研结论：ITAPI 是在线源里最准的；发表情吧（fabiaoqing）要特殊 TLS 和 Referer、斗图类网站内容老且有骂人图，没接；meme-generator 要下 415MB 素材，没装，低情商/高情商图已自己画。
- **头像来源**：nekos.best（全正经、带画师）和 Nekosia（`rating=safe`、带画师）；waifu.pics 已经关站。识图模型打分时要求半身或特写、颜色鲜亮、脸清楚，最好蓝紫发和猫耳，并给出头部位置，按头部裁成方图。两个图源都只许非商用、要保留画师署名：每次换头像的原图链接、画师和出处都记在 `avatars/index.json`，`/换头像` 的回复也会说画师。第一张已经换上（nekos.best，画师 krin）。
- **戳回去**：被群友戳时约 `poke_back_probability`（35%）也戳回去（`group_poke` / `friend_poke`），不戳小鲸鱼，免得两个机器人互戳停不下来。
- 3.8 Flash 不支持最低思考档，第一次报错后自动记住改用 LOW（存在 `gemini_usage.json`）。

## 2026-10-27 第四轮：对付小鲸鱼的打法、善意@、群百科、欢迎新人

- **对小鲸鱼：让它每次挑事都像个笑话，而不是跟它吵**。话是说给群友听的：情绪稳、不解释不自证、先护被骂的人再一句话把它变成笑话（打分、编成节目、点破漏洞、开玩笑地道德绑架、可怜它）。
- **吵架不再突然沉默**（`evil_stage`）：每波攻击都回（两次至少隔 `evil_cooldown_seconds` 12 秒，冷却里的回复是**延后发**不是丢掉）→ 第 `evil_max_rounds`（6）轮用一句“本期节目到此结束”式的梗收尾 → 之后它再骂只偶尔甩一张“你说得对/就这/急了”表情包（不花额度，最多 `evil_sticker_limit` 3 张、间隔 60 秒）→ 安静。有真人说话就重新开始。这样两个机器人不会无限刷屏，星姐也永远不像怂了。
- **善意 @**：模型在句首写 `[@名字]` 会变成真的 QQ @，只用来安慰、欢迎、夸奖、护人；只能 @ 最近聊天里出现过的真人，**永远不 @ 小鲸鱼**，一次最多一个，刚 @ 过的人不连着 @。`at_mention_enabled` 控制。
- **群百科**：被 @ 问问题时（“求助”场景）允许最多 5 条、每条 60 字、共 360 字（`answer_*`），先结论再理由/步骤/例子；拿不准的课程名、人名、版本号、数字宁可不提。被叫时优先用强模型。
- **欢迎新人**：有人进群（`group_increase`）星姐会 @ 他热情欢迎（`welcome_enabled`）。
- 测试改为全部写临时目录，不会再碰到正在运行的 `state.json`；启动时会丢掉未启用群的聊天记录。

## 2026-10-27 第五轮：不再整段沉默、先@再问也算问她、百科认真答

- **沉默的根因**：两个 Lite 模型各自超时一次就被暂停 3 分钟，恰好同时被暂停时连兜底模型都不试，那几分钟所有回复都是空的（主人 9:36 先 @ 再问的“詹姆斯和科比谁强”就是这么丢的）。现在：梯子上**最后一个今天还有额度的模型永远会试**；超时只暂停“同一类活”（识图超时不影响回话，`slow`）；忙（503）暂停 `busy_block_seconds` 300 秒。每条回复都会在日志里写一行“星姐回了（场景，模型）：…”，所有模型都答不上来也会写一行。
- **强模型额度**：免费档每个 Flash 每天约 20 次（3.5 Flash 的 429 写明了 20），各算各的。`premium_models` 现在是 3.6 Flash → 3.5 Flash → Gemini 3 Flash Preview → 3.7 / 3.8 Flash（后两个几乎总是 503，放最后）。每天太平洋时间零点（美东凌晨 3 点）恢复。主人和别人问她的问题总是先用强模型；对小鲸鱼和普通被叫只在当天强模型总共用了不到 `premium_shared_budget`（30）次时用。2.5 Flash 对新用户已下线，Omni 免费额度为 0。
- **先 @ 再问**：有人叫她（@、喊名字、回复她）之后 `follow_up_seconds`（60 秒）内他的下一条消息也算在跟她说话；她回了谁，谁的下一条也算。光 @ 一下（`@星姐`、`星姐在吗`）会多等 `bare_call_wait_seconds`（5 秒）看问题来没来，来了就一起答。这种“接着说”的消息不像真 @ 那样必须回，明显在跟别人说话时可以 `[SKIP]`。
- **百科认真答**：问她问题（被叫、接着说、私聊、主人问）都按百科答：第一句给明确结论，观点题要亮观点不和稀泥，离谱、难绷的问题一本正经地用真知识分析（认真本身就是笑点），最多 6 条（`answer_max_bubbles`）、400 字。主人问问题时先认真答好再撒娇，不再用“主人永远是对的”糊弄。问的是她自己（你是真人吗、我帅吗）还按原来的场景接。百科回答不带真人闲聊语料，免得被拉回闲聊。
- **小鲸鱼引用主人的消息骂他**也算怼主人（先护主）；聊天记录里引用会写成“[回复主人 名字：原话]”。判断小鲸鱼是不是在跑任务只看它自己说的话，不看引用内容。
- 低情商高情商图：模型把两栏写反、或者在栏里写了“低情商：”标签时自动纠正；两栏一样就不出图。
- **不再理小鲸鱼**（`evil_engage_enabled` 默认 false）：它的消息只当聊天背景，不回、不阴阳、不点评、不甩表情包，回答别人时也不提它。对付它的那套打法挪到了 `persona_evil.txt`，把开关改成 true 就恢复。学到的“爆梗”里拿小鲸鱼开玩笑的不再当平时的示范；群友吵架时的说话方式（对线、嘲讽、叫爸爸……）不再学，已学到的启动时自动丢掉。
- **问问题答得更好**：被问问题时模型用 `answer_thinking_level`（LOW）多想一步，输出上限 `answer_max_output_tokens` 1200；平时聊天还是最低思考档，保证快。
- **一次只回一条**：正在写或正在发一条回复时，新来的消息先排在待回复里按优先级合并（主人被叫 > 别人被叫 > 主人说话 > 其他），不会再一条条排队发出过时的回复。好几个人同时叫她时，晚到的人不会被丢：放进 `also`，这次一起按顺序答，每人两三条，先叫名字。
- “现在回答我……”不再被当成要联网查的新闻问题；“A vs B”“对比”算提问。回复里不会再出现“[主人]”“[邪恶人格]”这种程序标签。
- **闲聊先想三个角度再挑最好笑的**（`brainstorm_enabled`）：日常接话时模型按 JSON（`gemini_client.BRAINSTORM_SCHEMA`）一次写出三个真不一样的接法（顺着接、反转、谐音、一本正经胡说、已读乱回……，不拿自己是 AI 开玩笑），再挑一个“好笑又说得通”的发出去；日志里会写选中的角度（“星姐回了（闲聊·反转，…）”）。选中的那句和最近说过的话太像、或者带粗话时，直接换另外两个里合格的，不用再调一次模型。只多花输出字数，不多花调用次数。问问题、难过、联网查资料、欢迎新人不走这个，还是认真答一句。JSON 被截断时只用完整的那几句，坏掉的 JSON 绝不会发到群里。
- **看图更准**（`media.py`）：
  - 先在本机用苹果自带的文字识别（Live Text 同款引擎，`pyobjc-framework-Vision`，`ocr_enabled`）读出图上的字，约 0.05 秒一张、不花额度；读到的字作为提示交给 Gemini（“可能有错字，以图片为准”）。启动时会在后台预热一次（第一次要加载系统模型，约半分钟）。
  - 动图不再只看第一帧：均匀取 4 帧拼成 2×2 给模型，字从中间几帧读，模型按“动作怎么变”来描述。
  - 描述从 40 字放宽到 `vision_description_max_chars`（120）字，格式是“类型，主体在做什么；字“……”；情绪”：认得出的梗名、角色、名人直接写名字，图上的字原样照抄，多人图写清从左到右的顺序。
  - 识图最多等 `vision_total_timeout_seconds`（20 秒），以前最坏要等两分多钟，回复会卡在那里。Gemini 超时或 503 时，就用本机读出的字顶上（“图上的字：“绷不住了””）；这种临时描述不存缓存，下次再看到同一张图会重新让模型看。
- **测姻缘**（`matchmaker.py`，`matchmaker_enabled`）：
  - 怎么触发：发“测姻缘 A 和 B”“测一下A和B的姻缘”“A和B配不配”“测cp A B”，任意两样东西、人都行，不用 @ 她。“我”就是发消息的人，“你”就是星姐。
  - 分数：同一对东西永远同一个分数（按两个名字算的，顺序无所谓）；星姐和主人永远 100。
  - 回复：模型按这个分数写缘分类型、签文式判词、两三条解读和一句建议，程序画成一张“星姐姻缘鉴定书”（粉色卡片，有分数条和她的头像），配一句话发出去；模型答不上来时卡片照发。
  - 不会误触发：只说“测姻缘”没给两样东西，她会教用法；“他俩的缘分到头了”这种普通聊天不算。
- **算命**（`fortune.py`，`fortune_enabled`）：
  - 来源：排盘和黄历用 GitHub 上的 [6tail/lunar-python](https://github.com/6tail/lunar-python)（MIT，寿星万年历的 Python 版，算四柱八字、五行、十神、纳音、大运、节气和每天的宜忌），“每人每天一签”的玩法照 [MinatoAquaCrews/nonebot_plugin_fortune](https://github.com/MinatoAquaCrews/nonebot_plugin_fortune)。它的背景图是游戏、VTuber 同人图，没写授权，所以没搬，卡片是自己画的。
  - **八字**：发“算命 2003-08-01 08:30 男”，时间也可以写成“2001年3月5日晚上9点”“子时”“下午3点半”“农历2002年七月初七”。程序真实排盘：年月日时四柱、五行个数和缺什么、日主、纳音、十神、生肖、星座；给了性别还排大运，当前大运、今年流年和年龄也由程序算好。模型只照着这些数据写总评、性格、学业事业、感情、财运、今年运势和建议，画成一张“星姐算命馆”命盘图。不给时辰就只排三柱。
  - **今日运势**：发“今日运势”“抽签”“求签”。每人每天一签（大吉到大凶，按人和日期算，一整天都一样；主人不会抽到凶签），配今天黄历里真实的宜和忌、幸运色、幸运数字，模型写签诗和解签，画成“星姐神社”签图。同一天再抽会把同一支签再发一遍，不再调用模型。
  - **黄历**：发“今天黄历”，回农历日期、干支、宜忌、冲煞和节气，纯数据，不花额度。
  - 不会误触发：“我们班抽签分组了”“我昨天去算命了”这种句子不算，只有整句基本就是这个请求、或者 @ 她时才算。
- **冷场时多冒泡**：以前她说的最后一句没人接，就再也不主动开口；现在安静超过 `quiet_repeat_minutes`（90 分钟）可以再起一个话题，最多连续 `quiet_max_unanswered`（2）次没人接就停，有人说话后重新计数。冒泡时会随口招呼大家来测姻缘、抽签、算命。
- **掉线提醒**：电脑睡着（合盖、电池模式闲置几分钟）时星姐也跟着停；睡得久了 QQ 会被踢下线，NapCat 停在“请扫描二维码”，3001 端口不再应答。现在连不上 NapCat 超过 `offline_alert_seconds`（120 秒）会在这台 Mac 上弹一次通知“星姐掉线了”，日志里也写一行；重连日志前三次每次都写，之后大约一分钟一行，不再每 5 秒刷屏。运行 `./show_login_qr.sh` 会把 NapCat 当前的登录二维码复制出来、放大并打开，用登录着星姐 QQ 号的手机 QQ 扫码确认；二维码大约两分钟一换，过期再运行一次。
- **备用 Lite 模型**：`reply_models` 加了 `gemini-3.1-flash-lite-preview` 和 `gemini-flash-lite-latest`，Google 那边 3.5/3.1 Flash-Lite 超时或 503 时还有人接；模型返回空回复也算失败，换下一个。2.5 Flash-Lite 对新用户已下线。

## launchd 模板

`com.qqbot.plist` 是模板，不会自动加载。先在本机把所有 `REPLACE_...` 路径和 Key 占位符填好，建议设为仅本人可读（`chmod 600 com.qqbot.plist`），然后复制到 `~/Library/LaunchAgents/com.qqbot.plist`，运行：

```sh
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.qqbot.plist"
launchctl kickstart -k "gui/$(id -u)/com.qqbot"
```

日志路径也在 plist 中，需替换为真实绝对路径。NapCat 和 QQ 登录本身需先能运行。由于模板带占位符，不能直接加载。

## 注意

QQ 空间说说默认关闭。开启后通过 NapCat `get_cookies` 获取 `qzone.qq.com` Cookie，并调用非官方空间接口；接口可能变化，失败只写日志。图片生成额度为零或请求失败时同样只写日志，不影响群聊。
