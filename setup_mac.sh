#!/bin/zsh
set -euo pipefail

BOT_DIR="${0:A:h}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 10), "需要 Python 3.10+"'
"$PYTHON_BIN" -m venv "$BOT_DIR/.venv"
"$BOT_DIR/.venv/bin/python" -m pip install --upgrade pip
"$BOT_DIR/.venv/bin/python" -m pip install -r "$BOT_DIR/requirements.txt"
chmod 600 "$BOT_DIR/config.json" "$BOT_DIR/persona.txt"
echo "环境已安装：$BOT_DIR/.venv"
echo "在本机填写 config.json 中的 NapCat OneBot token 和 admin_qq_ids；仅在本机环境变量设置 GEMINI_API_KEY。"
