#!/bin/zsh
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
if colima status >/dev/null 2>&1; then
  exit 0
fi
colima start
