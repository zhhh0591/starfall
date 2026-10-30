# 把星姐搬到树莓派

你做第 1–4 步（买东西、写系统、开机联网），之后跟我说一声，剩下的我从 Mac 上远程装好。

## 1. 要准备的东西

- **树莓派 5，4GB 或 8GB 内存**。NapCat 里跑的是 Linux 版 QQ，比较吃内存，2GB 不够稳。手上已有 4GB 以上的树莓派 4 也行。
- **官方电源**：树莓派 5 用 27W USB-C 官方电源，树莓派 4 用 15W。供电不足会莫名其妙重启。
- **存储**：一张 64GB 左右的 A2 级 microSD 卡（三星 EVO、闪迪 Extreme 这类）。想更耐用可以换 USB 固态硬盘。
- **带散热的外壳**：树莓派 5 配官方主动散热器。它要 24 小时开着，会发热。
- **一根网线**：能插路由器就用网线，比 Wi-Fi 稳。
- **读卡器**：给 Mac 写系统用。

## 2. 在这台 Mac 上写系统

1. 从 raspberrypi.com/software 下载 **Raspberry Pi Imager** 并打开。
2. 设备选你的型号，系统选 **Raspberry Pi OS Lite (64-bit)**（不用桌面），存储选 SD 卡。
3. 点“下一步”，出现“使用自定义设置”时选“编辑设置”：
   - **通用**：
     - 主机名 `xingjie`，用户名 `xingjie`。密码自己设一个，自己记住，我不需要。
     - 不插网线的话填 Wi-Fi，时区选 `America/New_York`。
   - **服务**：勾“启用 SSH”，选“只允许公钥认证”，把下面这串公钥粘进去（已经复制到剪贴板了）：

     ```
     ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIABzZSIHcte4D0qgPq2InPHicvtI5MxRyQwYUfBaHeq4 xingjie-pi
     ```
4. 保存，写入，等它写完、校验完。

## 3. 开机联网

1. SD 卡插进树莓派，接网线（或者用刚设的 Wi-Fi），最后插电源，等两三分钟。
2. 树莓派要和这台 Mac 连在**同一个路由器或 Wi-Fi** 上，我才能用 `xingjie.local` 找到它。

> 学校宿舍那种要输账号密码的校园 Wi-Fi，树莓派一般连不上。通常要先在学校 IT 的设备注册页面登记它的 MAC 地址，或者用宿舍网口、自己的路由器，具体以学校 IT 的说明为准。树莓派和 Mac 不在一个网络里也有办法（装 Tailscale），到时候再说。

## 4. 跟我说“树莓派开好了”

## 我接下来做的

- **装环境**：连上树莓派，装 Docker 和 NapCat（和 Mac 上用的同一个镜像，支持树莓派），再装星姐要用的 Python。
- **搬数据**：从两个 GitHub 仓库拉下星姐（见下面）。Gemini Key 放进一个只有你能读的文件，不写进代码和配置。
- **换识字工具**：苹果那个识字插件只能在 Mac 上用。在树莓派上先不装它，看图照样用 Gemini；以后可以再换成开源的中文识字工具 RapidOCR。
- **开机自启**：NapCat 和星姐都设置成开机自动启动、崩溃自动重启。停电恢复或者重启之后，她自己就回来了。
- **扫码登录**：你用手机 QQ 扫一次码。换了设备登录，QQ 一定要扫码。

## 星姐现在放在哪

Mac 上的星姐已经停了，文件都在废纸篓里。她分成两个 GitHub 仓库：

- **`zhhh0591/starfall`**（公开）：代码、人设、示范对话、卡片素材、这份说明。`config.example.json` 是去掉了令牌和 QQ 号的示例配置。
- **`zhhh0591/starfall-data`**（私有）：真实配置 `config.json`（令牌已去掉）、聊天记忆、学到的说话方式和爆梗、收藏的群表情包、看图缓存、头像记录、真人语料。里面有群友的聊天内容，只能放私有仓库。

到树莓派上大致是这样（我连上后会替你做）：

```
git clone https://github.com/zhhh0591/starfall.git qq_bot
git clone https://github.com/zhhh0591/starfall-data.git
cp -R starfall-data/. qq_bot/        # 把记忆、语料和真实配置放回 qq_bot
```

还要补三样东西，都不在仓库里：

- **Gemini Key**：在 aistudio.google.com 的 API Keys 页面复制；Mac 上的旧副本只在废纸篓里的 `com.qqbot.plist` 中。
  - 想让 Gemini 用完后有别家接着聊，再加上这几家的免费 Key（都是可选的，有几个加几个）：`NVIDIA_API_KEY`、`GROQ_API_KEY`、`ZHIPU_API_KEY`、`MISTRAL_API_KEY`。去哪拿见 README 的“第六轮”。
- **NapCat 令牌**：在树莓派上新生成一个，填进 `config.json` 的 `access_token` 和 NapCat 的设置。
- **QQ 登录**：扫一次码。
