#!/usr/bin/env bash
# block-rm-rf.sh
# =========================================================================
# PreToolUse hook (matcher: Bash): rm -rf 系の破壊的コマンドをブロック
# profile.json で destructive_ops に "rm-rf" が含まれる時のみ配置される
#
# 設計:
#   - rm -rf / rm -fr / rm --recursive --force を検知
#   - /tmp 配下と mktemp 派生は許可
#   - 検出時は exit 2 + WHY/FIX
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

# rm -rf / rm -fr / rm --recursive --force パターン
if echo "$COMMAND" | grep -qE '\brm\s+(-[rf]*r[rf]*f|-[rf]*f[rf]*r|--recursive.*--force|--force.*--recursive)'; then
  # /tmp/ 配下なら許可
  if echo "$COMMAND" | grep -qE '\brm\s+[^|&;]*\s+/tmp/'; then
    exit 0
  fi
  # mktemp の結果削除なら許可
  if echo "$COMMAND" | grep -qE '\$\(mktemp'; then
    exit 0
  fi

  cat >&2 <<EOF
ERROR: 破壊的な rm -rf 実行を検知しブロックしました
WHY:   rm -rf は取り返しがつかない操作で、対象誤りが致命的になる
FIX:
  1. 本当に必要か再確認
  2. 対象が /tmp/ 配下なら問題なし (このチェックは自動パス)
  3. 恒常的にバイパスが必要なディレクトリは、このスクリプトの例外リストに追加
  4. 一度きりの例外なら、ユーザーが手動で実行してください

コマンド: ${COMMAND:0:200}
EOF
  exit 2
fi

exit 0
