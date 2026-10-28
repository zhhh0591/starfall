# 星姐二创图库

这个文件夹是机器人定时发到 QQ 群的图片来源。现有四张图是参照星姐头像生成的原创 Q 版场景图，不是从其他画师作品抓取的。

可以把自己创作、或已获得转载许可的 PNG、JPG、JPEG、WebP 图片放到这里。机器人会在白天随机时段从图库轮流选图，发过一轮再重新洗牌，不会连续重复同一张。图片文件不得超过 `config.json` 的 `fanart_max_file_mb`。文案可按文件名（去掉扩展名）在 `fanart_captions` 中设置。

默认每 24–72 小时随机发一张，只发到 `allowed_group_ids` 中的群。Gemini 图片请求回退默认关闭；如需重新启用，可设置 `fanart_gemini_fallback_enabled`。
