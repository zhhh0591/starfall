#!/bin/zsh
# QQ was logged out (the Mac slept too long, or QQ asked to log in again) and NapCat waits for a QR scan:
# copy NapCat's current QR code out of its container, enlarge it and open it. Scan it with the phone QQ
# that is logged in as 星姐's account. A code lasts about two minutes; run this again for a fresh one.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "$0")"
docker cp qqbot-napcat:/app/napcat/cache/qrcode.png ./login_qrcode.png
chmod 600 login_qrcode.png
.venv/bin/python -I - <<'EOF'
from PIL import Image
image = Image.open("login_qrcode.png").convert("L")
scale = max(1, 480 // max(image.size))
big = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
canvas = Image.new("L", (big.width + 80, big.height + 80), 255)
canvas.paste(big, (40, 40))
canvas.save("login_qrcode.png")
EOF
open login_qrcode.png
echo "二维码已经打开：用登录着星姐 QQ 号的手机 QQ 扫码并确认。过期了就再运行一次这个脚本。"
