#!/usr/bin/env bash
# gate-gradle-release.sh
# =========================================================================
# PreToolUse hook (matcher: Bash, MOBILE_PLATFORM_ANDROID=true のとき):
# gradle の release/signing task を PreToolUse で確認する
#
# 対象コマンド:
#   ./gradlew ... assembleRelease
#   ./gradlew ... bundleRelease
#   ./gradlew ... signingReport     (情報 dump だがリスクあり、一応 warn)
#   gradle ... publishReleaseApk...
#
# 動作:
#   - assembleRelease / bundleRelease は exit 2 でブロック
#   - signingReport は警告のみ (exit 0)
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

# gradle 呼び出し以外は対象外
if ! echo "$COMMAND" | grep -qE '\b(gradle|gradlew|\./gradlew)\b'; then
  exit 0
fi

# release build のパターン
if echo "$COMMAND" | grep -qE '\b(assembleRelease|bundleRelease|publishReleaseApk|publishReleaseBundle)\b'; then
  cat >&2 <<EOF
ERROR: gradle release build / publish を検知、ブロックしました
WHY:   release 署名を使う build は keystore を読み、公開用 artifact を作る。local での実行は rollback 不可能なリスクを含む
FIX:
  1. debug build を意図していたなら 'assembleDebug' / 'bundleDebug' に変更
  2. 本当に release が必要なら:
     a. fastlane lane を使う
     b. CI (GitHub Actions / Bitrise) で実行
     c. この hook を .claude/settings.local.json で一時 bypass

コマンド: ${COMMAND:0:200}
EOF
  exit 2
fi

# signingReport は情報 leak 可能性
if echo "$COMMAND" | grep -qE '\bsigningReport\b'; then
  cat >&2 <<EOF
⚠ NOTICE: gradle signingReport は署名設定 (keystore alias など) を stdout に dump します。
  コンソール出力が共有されないよう注意してください。
EOF
  exit 0
fi

exit 0
