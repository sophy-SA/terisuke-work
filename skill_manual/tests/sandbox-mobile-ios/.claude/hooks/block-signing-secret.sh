#!/usr/bin/env bash
# block-signing-secret.sh
# =========================================================================
# PreToolUse hook (matcher: Edit|Write): モバイル署名情報 / 秘密情報を commit
# または repo 内に配置する試みをブロック
#
# 対象ファイル:
#   - iOS: *.p12, *.mobileprovision, ExportOptions.plist (AppleID 含む場合)
#   - Android: *.jks, *.keystore, keystore.properties, google-services.json
#   - Firebase: GoogleService-Info.plist
#   - fastlane: Appfile (Apple ID 記載)、Matchfile (git-based cert storage の credentials)
#
# 動作:
#   - 成功時 exit 0 (無言)
#   - ブロック時 exit 2 + stderr に WHY/FIX
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
LOWER=$(echo "$BASENAME" | tr '[:upper:]' '[:lower:]')

BLOCKED=""
REASON=""

case "$LOWER" in
  *.p12|*.cer|*.certSigningRequest)
    BLOCKED="iOS 署名証明書"
    REASON="p12/cer 等の証明書ファイルは絶対に repo に入れない"
    ;;
  *.mobileprovision)
    BLOCKED="iOS Provisioning Profile"
    REASON="provisioning profile は Apple Developer Portal から随時取得するべき"
    ;;
  *.jks|*.keystore)
    BLOCKED="Android Keystore"
    REASON="keystore は本番署名の秘密鍵そのもの。漏洩したら app 乗っ取り可能"
    ;;
  keystore.properties)
    BLOCKED="Android keystore パスワード設定"
    REASON="keystore.properties は署名パスワードを含む"
    ;;
  google-services.json)
    BLOCKED="Android Firebase 設定"
    REASON="Firebase API 秘密鍵を含む可能性"
    ;;
  googleservice-info.plist)
    BLOCKED="iOS Firebase 設定"
    REASON="Firebase API 秘密鍵を含む可能性"
    ;;
  appfile|matchfile)
    BLOCKED="fastlane 認証情報"
    REASON="AppleID や match repo credential を含む"
    ;;
esac

# パターンマッチでも追加判定 (拡張子だけでない場合)
if [[ -z "$BLOCKED" ]]; then
  case "$FILE_PATH" in
    */provisioning/*|*/certificates/*|*/signing/*)
      BLOCKED="署名関連ディレクトリ"
      REASON="signing / certificates / provisioning ディレクトリは外部管理するべき"
      ;;
  esac
fi

if [[ -n "$BLOCKED" ]]; then
  cat >&2 <<EOF
ERROR: $BLOCKED を repo 内に配置しようとしています ($FILE_PATH)
WHY:   $REASON。一度 git に入ると履歴から完全削除は困難で、漏洩扱いになり証明書の revoke が必要
FIX:
  1. ファイルを外部に移す (e.g., macOS Keychain / Vault / 1Password)
  2. CI 環境変数から展開する
  3. fastlane match を使う (encrypted git repo で cert 管理)
  4. .gitignore に該当拡張子を追加:
       *.p12
       *.mobileprovision
       *.jks
       *.keystore
       keystore.properties
       google-services.json
       GoogleService-Info.plist
  5. 既に commit 済みなら git filter-repo で履歴から削除 + cert rotation
EOF
  exit 2
fi

exit 0
