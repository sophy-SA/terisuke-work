#!/usr/bin/env bash
# block-secret-commit.sh
# =========================================================================
# PreToolUse hook (matcher: Bash): 秘密情報っぽい文字列を含むコミットをブロック
# profile.json で handles_secrets=true の時のみ配置される
#
# 設計:
#   - 対象は 'git commit' 系の Bash コマンド実行
#   - 成功時 (検出なし) は exit 0, 無言
#   - 検出時は exit 2 + WHY/FIX 形式の stderr
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

# git commit 系以外は対象外
if ! echo "$COMMAND" | grep -qE '\bgit\s+commit\b'; then
  exit 0
fi

# 直前の staged 差分を取得
DIFF=$(git diff --cached 2>/dev/null || echo "")

if [[ -z "$DIFF" ]]; then
  exit 0
fi

# 秘密情報パターン
PATTERNS=(
  '(?i)(api[_-]?key|secret|password|passwd|token)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"']{8,}'
  'AKIA[0-9A-Z]{16}'
  'sk-[A-Za-z0-9]{32,}'
  'ghp_[A-Za-z0-9]{36}'
  'xox[baprs]-[A-Za-z0-9-]{10,}'
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
)

MATCHED=""
for p in "${PATTERNS[@]}"; do
  if HIT=$(echo "$DIFF" | grep -iE "$p" 2>/dev/null); then
    MATCHED+="  - Pattern: $p"$'\n'
    MATCHED+="    Match: ${HIT:0:120}..."$'\n'
  fi
done

if [[ -n "$MATCHED" ]]; then
  cat >&2 <<EOF
ERROR: コミットに秘密情報の疑いが含まれています
WHY:   API キー / トークン / 秘密鍵が git 履歴に入ると、後から削除しても漏洩扱いになります
FIX:
  1. 該当行を .env や Secret Manager に移す
  2. .env を .gitignore に追加
  3. git reset HEAD で unstage してから再構成
  4. 誤って push 済みの場合は、漏洩としてキーローテーション必須

検出されたパターン:
$MATCHED

バイパスが必要な (誤検出の) 場合は、このファイル .claude/hooks/block-secret-commit.sh を編集してください。
EOF
  exit 2
fi

exit 0
