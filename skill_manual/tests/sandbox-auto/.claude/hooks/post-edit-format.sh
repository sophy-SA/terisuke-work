#!/usr/bin/env bash
# post-edit-format.sh
# =========================================================================
# PostToolUse hook: Edit/Write 後に編集対象ファイルを自動整形する
#
# 設計:
#   - 成功時は無言 (back-pressure 原則)
#   - 失敗時は exit 2 + stderr に WHY / FIX 形式
#   - 対応言語の formatter が未インストールなら silent skip
#   - 対象外ファイルなら silent skip
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

if [[ -z "$FILE_PATH" ]] || [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# 拡張子ベースで formatter を選択
EXT="${FILE_PATH##*.}"

run_formatter() {
  local cmd="$1"
  shift
  if ! command -v "$cmd" &>/dev/null; then
    # formatter が無い場合は silent skip
    exit 0
  fi
  if ! "$cmd" "$@" &>/dev/null; then
    cat >&2 <<EOF
ERROR: $cmd が $FILE_PATH の整形に失敗
WHY:   コードに構文エラーがあるか、formatter の設定が不整合
FIX:   手動で '$cmd $FILE_PATH' を実行しエラー内容を確認、元の構文を修正してから再コミット
EOF
    exit 2
  fi
}

case "$EXT" in
  py)
    # Python: ruff format (推奨) > black の順で試す
    if command -v ruff &>/dev/null; then
      run_formatter ruff format "$FILE_PATH"
    elif command -v black &>/dev/null; then
      run_formatter black --quiet "$FILE_PATH"
    fi
    ;;
  ts|tsx|js|jsx|mjs|cjs)
    # TS/JS: biome (推奨) > prettier の順
    if command -v biome &>/dev/null; then
      run_formatter biome format --write "$FILE_PATH"
    elif command -v prettier &>/dev/null; then
      run_formatter prettier --write --log-level=silent "$FILE_PATH"
    fi
    ;;
  go)
    run_formatter gofmt -w "$FILE_PATH"
    ;;
  rs)
    if command -v rustfmt &>/dev/null; then
      run_formatter rustfmt "$FILE_PATH"
    fi
    ;;
  sh|bash)
    if command -v shfmt &>/dev/null; then
      run_formatter shfmt -w "$FILE_PATH"
    fi
    ;;
  json)
    if command -v jq &>/dev/null; then
      # jq は上書きモードを持たないので一時ファイル経由
      TMP=$(mktemp)
      if jq '.' "$FILE_PATH" > "$TMP" 2>/dev/null; then
        mv "$TMP" "$FILE_PATH"
      else
        rm -f "$TMP"
        cat >&2 <<EOF
ERROR: JSON パースエラー ($FILE_PATH)
WHY:   ファイルが有効な JSON でない
FIX:   引用符・カンマ・括弧を確認して修正
EOF
        exit 2
      fi
    fi
    ;;
  md|markdown)
    if command -v prettier &>/dev/null; then
      run_formatter prettier --write --log-level=silent "$FILE_PATH"
    fi
    ;;
esac

exit 0
