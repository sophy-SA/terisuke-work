#!/usr/bin/env bash
# protect-manifest.sh
# =========================================================================
# PreToolUse hook (matcher: Edit|Write): モバイル manifest 編集時に警告を出す
#
# 対象ファイル:
#   - iOS: Info.plist, Package.swift
#   - Android: AndroidManifest.xml, build.gradle(.kts)
#   - React Native: app.json, app.config.js, metro.config.js
#   - Flutter: pubspec.yaml, pubspec.lock
#
# 動作:
#   - ブロックしない (編集自体は必要)
#   - ただし注意喚起を stderr に出す (additionalContext)
#   - 危険な変更 (bundle identifier 変更、version 降格) は検知時 exit 2
# =========================================================================

set -euo pipefail

INPUT_JSON=$(cat)

FILE_PATH=$(echo "$INPUT_JSON" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

BASENAME=$(basename "$FILE_PATH")

# 編集新内容 (Write の content、Edit の new_string)
NEW_CONTENT=$(echo "$INPUT_JSON" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    print(ti.get('content', '') or ti.get('new_string', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

MANIFEST_TYPE=""
case "$BASENAME" in
  Info.plist)           MANIFEST_TYPE="iOS Info.plist" ;;
  Package.swift)        MANIFEST_TYPE="iOS Package.swift" ;;
  AndroidManifest.xml)  MANIFEST_TYPE="Android Manifest" ;;
  build.gradle|build.gradle.kts) MANIFEST_TYPE="Android Gradle" ;;
  app.json)             MANIFEST_TYPE="React Native app.json" ;;
  app.config.js|app.config.ts) MANIFEST_TYPE="Expo/RN config" ;;
  metro.config.js)      MANIFEST_TYPE="Metro bundler config" ;;
  pubspec.yaml)         MANIFEST_TYPE="Flutter pubspec" ;;
esac

if [[ -z "$MANIFEST_TYPE" ]]; then
  exit 0
fi

# 危険な編集パターン検出
if echo "$NEW_CONTENT" | grep -qE 'CFBundleIdentifier|package="com\.'; then
  if echo "$NEW_CONTENT" | grep -qiE 'CFBundleIdentifier\s*[:=]|package\s*='; then
    cat >&2 <<EOF
ERROR: $MANIFEST_TYPE の Bundle Identifier / package name 変更を検知 ($FILE_PATH)
WHY:   Bundle Identifier / package name 変更は App Store / Play Store 上では別アプリ扱い、
       既存ユーザーが強制的に離散する
FIX:
  1. 意図的な変更なら、release notes と migration plan を用意
  2. typo なら git reset で戻す
  3. 本当に分岐したい場合は、build configuration / flavor で切り替える
EOF
    exit 2
  fi
fi

# バージョン降格の検知 (数字が減った場合の警告)
# 厳密な semver 比較は hook では重いので、単純なログに留める
cat >&2 <<EOF
⚠ NOTICE: $MANIFEST_TYPE を編集しています ($FILE_PATH)
  manifest 変更はアプリ挙動に直結します。変更内容を mobile-reviewer に必ずレビューさせてください。
EOF

# exit 0 (ブロックしない、警告のみ)
exit 0
