#!/usr/bin/env bash
# install.sh
# =========================================================================
# harness-forge の 3 skill を ~/.claude/skills/ に symlink する。
# シンボリックリンクにすることで、repo 側の更新が即座に反映される。
#
# Usage:
#   bash install.sh              — symlink で install
#   bash install.sh --copy       — symlink ではなく copy (将来変更があった時の安定性優先)
#   bash install.sh --uninstall  — アンインストール (uninstall.sh を呼ぶ)
#
# 前提:
#   - ~/.claude/ が存在する (Claude Code が1回でも起動済み)
#   - python3 が利用可能
# =========================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
ASSETS_DIR="$REPO_ROOT/assets"

MODE="symlink"
if [[ "${1:-}" == "--copy" ]]; then
  MODE="copy"
elif [[ "${1:-}" == "--uninstall" ]]; then
  bash "$REPO_ROOT/uninstall.sh"
  exit 0
fi

# 前提確認
if [[ ! -d "$HOME/.claude" ]]; then
  echo "ERROR: ~/.claude/ が無い。Claude Code を1回起動してから再実行してください。" >&2
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 が必要です。" >&2
  exit 1
fi

mkdir -p "$SKILLS_DIR"

SKILLS=("harness-profiler" "harness-generator" "harness-validator")
INSTALLED=()
SKIPPED=()

for skill in "${SKILLS[@]}"; do
  SRC="$REPO_ROOT/skills/$skill"
  DEST="$SKILLS_DIR/$skill"

  if [[ ! -d "$SRC" ]]; then
    echo "WARN: source $SRC が見つからない、skip" >&2
    SKIPPED+=("$skill (source missing)")
    continue
  fi

  # 既存ディレクトリが symlink でない場合、上書きしない
  if [[ -e "$DEST" ]] && [[ ! -L "$DEST" ]]; then
    echo "WARN: $DEST は symlink ではない既存ディレクトリ。手動で削除してから再実行してください。" >&2
    SKIPPED+=("$skill (dest exists as dir)")
    continue
  fi

  # 既存の symlink は削除
  if [[ -L "$DEST" ]]; then
    rm -f "$DEST"
  fi

  if [[ "$MODE" == "symlink" ]]; then
    ln -s "$SRC" "$DEST"
    INSTALLED+=("$skill (symlink)")
  else
    cp -r "$SRC" "$DEST"
    INSTALLED+=("$skill (copy)")
  fi
done

echo ""
echo "=========================================="
echo "harness-forge install 完了"
echo "=========================================="
echo ""
echo "Installed:"
for s in "${INSTALLED[@]}"; do
  echo "  ✓ $s"
done
if [[ ${#SKIPPED[@]} -gt 0 ]]; then
  echo ""
  echo "Skipped:"
  for s in "${SKIPPED[@]}"; do
    echo "  - $s"
  done
fi

echo ""
echo "Assets (archetypes / templates / schemas):"
echo "  $ASSETS_DIR"
echo ""
echo "注意: scripts は以下の順で assets を解決します:"
echo "  1. HARNESS_FORGE_ASSETS 環境変数 (明示)"
echo "  2. Script 自身の location から相対 (symlink install 時は repo を follow)"
echo "  3. エラー"
echo ""
echo "symlink install なら通常設定不要ですが、repo を移動する場合は環境変数を設定してください:"
echo "  export HARNESS_FORGE_ASSETS=$ASSETS_DIR"
echo ""
echo "Claude Code 側でスキル認識:"
echo "  - Claude Code を再起動、または /agents コマンドで Library タブを開く"
echo "  - '/harness-profiler', '/harness-generator', '/harness-validator' が menu に出れば OK"
echo ""
echo "アンインストール:"
echo "  bash $REPO_ROOT/uninstall.sh"
