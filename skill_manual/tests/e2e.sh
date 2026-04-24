#!/usr/bin/env bash
# tests/e2e.sh
# =========================================================================
# harness-forge の end-to-end 動作検証
#
# 実行順:
#   1. サンドボックスディレクトリ作成
#   2. fixture profile.json 配置
#   3. harness-generator の apply_scaffold.py を直接実行 (skill 経由ではなく)
#   4. 生成物の assert
#   5. harness-validator の run_all.py を直接実行
#   6. errors==0 確認
#   7. 破壊テスト (CLAUDE.md を 200 行に水増し) → C01 WARN fire 確認
#   8. 秘密情報 fixture でも実行 → conditional hook (block-secret-commit, block-rm-rf) 確認
#
# Exit:
#   0  全テスト pass
#   1  環境セットアップエラー
#   2  assertion failed
# =========================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="$REPO_ROOT/tests/sandbox"
FIXTURE_PROFILE="$REPO_ROOT/tests/fixtures/profile.daily-utility.json"
FIXTURE_PROFILE_SECRETS="$REPO_ROOT/tests/fixtures/profile.daily-utility-with-secrets.json"

GENERATOR_SCRIPT="$REPO_ROOT/skills/harness-generator/scripts/apply_scaffold.py"
VALIDATOR_SCRIPT="$REPO_ROOT/skills/harness-validator/scripts/run_all.py"
SCHEMA="$REPO_ROOT/assets/knowledge/schema/profile.schema.json"
ARCHETYPES_DIR="$REPO_ROOT/assets/archetypes"
TEMPLATES_DIR="$REPO_ROOT/assets/templates"

fail() {
  echo "ASSERTION FAILED: $*" >&2
  exit 2
}

info() {
  echo "[e2e] $*"
}

# 依存確認
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 が必要" >&2
  exit 1
fi

# ---- Test 1: Clean scaffold for daily-utility ----
info "Test 1: Clean scaffold (daily-utility fixture)"
rm -rf "$SANDBOX"
mkdir -p "$SANDBOX"
cp "$FIXTURE_PROFILE" "$SANDBOX/profile.json"

(cd "$SANDBOX" && python3 "$GENERATOR_SCRIPT" \
  --profile ./profile.json \
  --archetypes-dir "$ARCHETYPES_DIR" \
  --templates-dir "$TEMPLATES_DIR" \
  --schema "$SCHEMA")

# 期待ファイル assert
for expected in \
  "CLAUDE.md" \
  ".claude/subagents/reviewer.md" \
  ".claude/hooks/post-edit-format.sh" \
  ".claude/hooks/pre-commit-lint.sh" \
  ".claude/settings.json" \
  "docs/harness.md" \
  ".harness-forge.state.json"; do
  if [[ ! -f "$SANDBOX/$expected" ]]; then
    fail "期待ファイルが無い: $expected"
  fi
done
info "  ✓ 期待ファイル 7 件確認"

# CLAUDE.md 行数 ≤ 50
CLAUDE_LINES=$(wc -l < "$SANDBOX/CLAUDE.md")
if [[ "$CLAUDE_LINES" -gt 50 ]]; then
  fail "CLAUDE.md が 50 行超: $CLAUDE_LINES 行"
fi
info "  ✓ CLAUDE.md は $CLAUDE_LINES 行 (≤50)"

# settings.json が有効 JSON
if ! python3 -m json.tool "$SANDBOX/.claude/settings.json" >/dev/null; then
  fail "settings.json が無効 JSON"
fi
info "  ✓ settings.json パース OK"

# hook scripts 実行権限
for h in "$SANDBOX/.claude/hooks/post-edit-format.sh" "$SANDBOX/.claude/hooks/pre-commit-lint.sh"; do
  if [[ ! -x "$h" ]]; then
    fail "$h に実行権限なし"
  fi
done
info "  ✓ hook scripts 実行可能"

# state.json に files_written が記録されている
if ! python3 -c "
import json
s = json.load(open('$SANDBOX/.harness-forge.state.json'))
assert 'files_written' in s and len(s['files_written']) > 0
assert s.get('archetype_primary') == 'daily-utility'
" 2>/dev/null; then
  fail "state.json の内容が不正"
fi
info "  ✓ state.json 記録 OK"

# ---- Test 2: Idempotent re-run ----
info "Test 2: Idempotent re-run (no-op 判定)"
(cd "$SANDBOX" && python3 "$GENERATOR_SCRIPT" \
  --profile ./profile.json \
  --archetypes-dir "$ARCHETYPES_DIR" \
  --templates-dir "$TEMPLATES_DIR" \
  --schema "$SCHEMA") 2>&1 | grep -q "変化なし" || {
    info "  ⚠ idempotent hint メッセージが出ていない (警告のみ)"
  }
info "  ✓ 再実行完走"

# ---- Test 3: Validator green ----
info "Test 3: Validator run (errors==0 期待)"
(cd "$SANDBOX" && python3 "$VALIDATOR_SCRIPT" \
  --target . \
  --output-json ./harness-report.json \
  --output-md ./harness-report.md \
  --profile ./profile.json)

ERRORS=$(python3 -c "
import json
r = json.load(open('$SANDBOX/harness-report.json'))
print(r['summary']['errors'])
")
if [[ "$ERRORS" -ne 0 ]]; then
  fail "validator が $ERRORS 個の error を報告"
fi
info "  ✓ errors == 0"

# ---- Test 4: 破壊テスト — CLAUDE.md を 200 行に水増し ----
info "Test 4: 破壊テスト (CLAUDE.md 200 行水増し) → C01 WARN fire"
{
  cat "$SANDBOX/CLAUDE.md"
  for i in $(seq 1 200); do echo "filler line $i"; done
} > "$SANDBOX/CLAUDE.md.new"
mv "$SANDBOX/CLAUDE.md.new" "$SANDBOX/CLAUDE.md"

(cd "$SANDBOX" && python3 "$VALIDATOR_SCRIPT" \
  --target . \
  --output-json ./harness-report.json \
  --output-md ./harness-report.md \
  --profile ./profile.json) || true  # WARNING 時は exit 0 のはず

if ! grep -q "C01" "$SANDBOX/harness-report.md"; then
  fail "CLAUDE.md 水増し後に C01 が fire していない"
fi
info "  ✓ C01 WARN fire 確認"

# ---- Test 5: 秘密情報 fixture で conditional hook 生成確認 ----
info "Test 5: handles_secrets=true fixture で conditional hook"
SANDBOX_SEC="$REPO_ROOT/tests/sandbox-secrets"
rm -rf "$SANDBOX_SEC"
mkdir -p "$SANDBOX_SEC"
cp "$FIXTURE_PROFILE_SECRETS" "$SANDBOX_SEC/profile.json"

(cd "$SANDBOX_SEC" && python3 "$GENERATOR_SCRIPT" \
  --profile ./profile.json \
  --archetypes-dir "$ARCHETYPES_DIR" \
  --templates-dir "$TEMPLATES_DIR" \
  --schema "$SCHEMA")

if [[ ! -f "$SANDBOX_SEC/.claude/hooks/block-secret-commit.sh" ]]; then
  fail "handles_secrets=true なのに block-secret-commit.sh が生成されていない"
fi
if [[ ! -f "$SANDBOX_SEC/.claude/hooks/block-rm-rf.sh" ]]; then
  fail "destructive_ops=[rm-rf] なのに block-rm-rf.sh が生成されていない"
fi
info "  ✓ conditional hooks 生成 OK"

# ---- Test 6: Merge mode (既存プロジェクト保護) ----
info "Test 6: Merge mode (skip_if_exists + json-deep)"
SANDBOX_MERGE="$REPO_ROOT/tests/sandbox-merge"
FIXTURE_EXISTING="$REPO_ROOT/tests/fixtures/existing-project"
rm -rf "$SANDBOX_MERGE"
mkdir -p "$SANDBOX_MERGE"
cp -r "$FIXTURE_EXISTING/." "$SANDBOX_MERGE/"
cp "$FIXTURE_PROFILE" "$SANDBOX_MERGE/profile.json"

# existing_claude_dir=true は fixture に無いが、merge mode は既存ファイル検出で動く
(cd "$SANDBOX_MERGE" && python3 "$GENERATOR_SCRIPT" \
  --profile ./profile.json \
  --archetypes-dir "$ARCHETYPES_DIR" \
  --templates-dir "$TEMPLATES_DIR" \
  --schema "$SCHEMA")

# skip_if_exists: 既存 CLAUDE.md の "absolutely 保護" 行が残っているか
if ! grep -q "absolutely 保護" "$SANDBOX_MERGE/CLAUDE.md"; then
  fail "既存 CLAUDE.md の保護対象行が失われた (skip_if_exists 失敗)"
fi
info "  ✓ skip_if_exists で既存 CLAUDE.md 保護"

# json-deep: 既存 permissions.allow が残っているか
if ! python3 -c "
import json
s = json.load(open('$SANDBOX_MERGE/.claude/settings.json'))
assert 'Bash(my-custom-tool:*)' in s['permissions']['allow'], 'ユーザー permission が消えた'
assert 'Bash(ruff:*)' in s['permissions']['allow'], '生成 permission が merge されていない'
assert s.get('theme') == 'dark', 'theme が失われた'
assert 'SessionStart' in s.get('hooks', {}), 'ユーザー SessionStart hook が失われた'
assert 'PostToolUse' in s.get('hooks', {}), '生成 PostToolUse hook が merge されていない'
" 2>&1; then
  fail "settings.json の json-deep merge が想定と異なる"
fi
info "  ✓ json-deep で既存 permissions + theme + hooks 保護、生成側も merge"

# ---- Cleanup ----
info ""
info "========================================"
info "All E2E tests passed 🎉"
info "========================================"
echo "E2E passed"
exit 0
