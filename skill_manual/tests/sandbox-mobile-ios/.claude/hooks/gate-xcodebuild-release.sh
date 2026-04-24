#!/usr/bin/env bash
# gate-xcodebuild-release.sh
# =========================================================================
# PreToolUse hook (matcher: Bash, MOBILE_PLATFORM_IOS=true のとき): xcodebuild の
# 本番 release build / archive を PreToolUse で確認する
#
# 対象コマンド:
#   xcodebuild ... -configuration Release ...
#   xcodebuild ... archive ...
#   xcodebuild ... -exportArchive ...
#
# 動作:
#   - 上記コマンドを検知したら exit 2 でブロックし、理由を説明
#   - 通常の debug build や test は通過
# =========================================================================

set -euo pipefail

INPUT_JSON=$(cat)

COMMAND=$(echo "$INPUT_JSON" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# xcodebuild 以外は対象外
if ! echo "$COMMAND" | grep -qE '\bxcodebuild\b'; then
  exit 0
fi

# release build / archive / exportArchive のパターン
if echo "$COMMAND" | grep -qE -- '-configuration\s+Release|\barchive\b|-exportArchive'; then
  cat >&2 <<EOF
ERROR: xcodebuild による release build / archive / export を検知、ブロックしました
WHY:   本番署名を使う release build は、local 環境の設定差分や証明書の扱いミスが直接リリースに影響する
FIX:
  1. debug build か test を意図していたなら、'-configuration Debug' に変えるか 'test' サブコマンドを使う
  2. 本当に release build が必要なら、以下のどれかを選択:
     a. fastlane lane を使う (手順が固定化されたワークフロー)
     b. CI (GitHub Actions macOS runner / Xcode Cloud) で実行
     c. 一時的に手動実行したい場合、この hook を一時 bypass (.claude/settings.local.json で deny)

コマンド: ${COMMAND:0:200}
EOF
  exit 2
fi

exit 0
