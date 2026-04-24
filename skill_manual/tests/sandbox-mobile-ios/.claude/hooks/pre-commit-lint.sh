#!/usr/bin/env bash
# pre-commit-lint.sh
# =========================================================================
# git pre-commit hook 本体として動作する lint ゲート。
# 言語別 linter を差分ファイルにのみ実行し、速度を保つ。
#
# 設計:
#   - 成功時は無言 (back-pressure 原則)
#   - 失敗時は exit 1 (git 慣例) + stderr に WHY / FIX
#   - linter 未インストールの言語は silent skip
#   - staged ファイルのみ対象 (full repo lint はしない)
# =========================================================================

set -euo pipefail

# staged ファイル (Added/Modified のみ、削除は対象外)
STAGED=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null || echo "")

if [[ -z "$STAGED" ]]; then
  exit 0
fi

FAILED=0

lint_file() {
  local file="$1"
  local ext="${file##*.}"
  local cmd_output=""

  case "$ext" in
    py)
      if command -v ruff &>/dev/null; then
        if ! cmd_output=$(ruff check "$file" 2>&1); then
          cat >&2 <<EOF
ERROR: ruff が $file で違反を検出
WHY:   Python コードが lint ルールに違反 (構文エラー / 未使用 import / 命名規則等)
FIX:   'ruff check --fix $file' で自動修正可能なものを直す。残りは手動で対応
--- ruff output ---
$cmd_output
---
EOF
          FAILED=1
        fi
      fi
      ;;
    ts|tsx|js|jsx|mjs|cjs)
      if command -v biome &>/dev/null; then
        if ! cmd_output=$(biome lint "$file" 2>&1); then
          cat >&2 <<EOF
ERROR: biome lint が $file で違反を検出
WHY:   TypeScript/JavaScript コードが lint ルールに違反
FIX:   'biome check --write $file' で自動修正。残りは手動対応
--- biome output ---
$cmd_output
---
EOF
          FAILED=1
        fi
      elif command -v eslint &>/dev/null; then
        if ! cmd_output=$(eslint "$file" 2>&1); then
          cat >&2 <<EOF
ERROR: eslint が $file で違反を検出
WHY:   TypeScript/JavaScript コードが lint ルールに違反
FIX:   'eslint --fix $file' で自動修正。残りは手動対応
--- eslint output ---
$cmd_output
---
EOF
          FAILED=1
        fi
      fi
      ;;
    go)
      if command -v go &>/dev/null; then
        if ! cmd_output=$(gofmt -l "$file" 2>&1); then
          FAILED=1
        fi
        if [[ -n "$cmd_output" ]]; then
          cat >&2 <<EOF
ERROR: gofmt 違反 ($file)
WHY:   Go ファイルが gofmt 整形済みでない
FIX:   'gofmt -w $file' を実行してから git add
EOF
          FAILED=1
        fi
        if command -v go &>/dev/null && [[ -f go.mod ]]; then
          if ! cmd_output=$(go vet "./...$file" 2>&1); then
            : # go vet エラーは警告扱い (パッケージ単位実行なので file 限定困難)
          fi
        fi
      fi
      ;;
    rs)
      if command -v cargo &>/dev/null; then
        if ! cmd_output=$(cargo clippy --quiet --manifest-path=Cargo.toml 2>&1); then
          cat >&2 <<EOF
ERROR: cargo clippy が違反を検出
WHY:   Rust コードが lint ルールに違反
FIX:   'cargo clippy --fix' で一部自動修正、残りは手動対応
--- clippy output ---
$cmd_output
---
EOF
          FAILED=1
        fi
      fi
      ;;
    sh|bash)
      if command -v shellcheck &>/dev/null; then
        if ! cmd_output=$(shellcheck "$file" 2>&1); then
          cat >&2 <<EOF
ERROR: shellcheck が $file で違反を検出
WHY:   シェルスクリプトに潜在的な問題
FIX:   shellcheck の指摘 (SC番号) を参照: https://www.shellcheck.net/wiki/
--- shellcheck output ---
$cmd_output
---
EOF
          FAILED=1
        fi
      fi
      ;;
    json)
      if command -v python3 &>/dev/null; then
        if ! python3 -m json.tool "$file" >/dev/null 2>&1; then
          cat >&2 <<EOF
ERROR: $file が有効な JSON でない
WHY:   構文エラー (引用符・カンマ・括弧の不整合)
FIX:   python3 -m json.tool $file でエラー箇所を確認
EOF
          FAILED=1
        fi
      fi
      ;;
    yml|yaml)
      if command -v python3 &>/dev/null; then
        if ! python3 -c "import yaml, sys; yaml.safe_load(open('$file'))" 2>/dev/null; then
          cat >&2 <<EOF
ERROR: $file が有効な YAML でない
WHY:   インデント・コロン・クォートの不整合
FIX:   python3 -c "import yaml; yaml.safe_load(open('$file'))" でエラー確認
EOF
          FAILED=1
        fi
      fi
      ;;
  esac
}

for f in $STAGED; do
  if [[ -f "$f" ]]; then
    lint_file "$f"
  fi
done

if [[ $FAILED -ne 0 ]]; then
  cat >&2 <<EOF

pre-commit lint gate がブロックしました。
詳細は上記 stderr を参照し、修正後に再度 git add + git commit してください。
緊急でバイパスしたい場合は git commit --no-verify ですが、CLAUDE.md の禁止事項です。
EOF
  exit 1
fi

exit 0
