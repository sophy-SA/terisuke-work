#!/usr/bin/env bash
# uninstall.sh
# =========================================================================
# harness-forge skill の symlink / copy を ~/.claude/skills/ から削除する。
# Usage: bash uninstall.sh
# =========================================================================

set -euo pipefail

SKILLS_DIR="$HOME/.claude/skills"
SKILLS=("harness-profiler" "harness-generator" "harness-validator")

REMOVED=()
NOT_FOUND=()

for skill in "${SKILLS[@]}"; do
  DEST="$SKILLS_DIR/$skill"
  if [[ -L "$DEST" ]]; then
    rm "$DEST"
    REMOVED+=("$skill (symlink removed)")
  elif [[ -d "$DEST" ]]; then
    # copy install されている可能性。確認プロンプト
    echo "$DEST はディレクトリ (copy install の可能性)。削除しますか? [y/N]"
    read -r answer
    if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
      rm -rf "$DEST"
      REMOVED+=("$skill (dir removed)")
    else
      NOT_FOUND+=("$skill (skipped by user)")
    fi
  else
    NOT_FOUND+=("$skill (not installed)")
  fi
done

echo ""
echo "=========================================="
echo "harness-forge uninstall 完了"
echo "=========================================="

if [[ ${#REMOVED[@]} -gt 0 ]]; then
  echo "Removed:"
  for s in "${REMOVED[@]}"; do
    echo "  ✓ $s"
  done
fi
if [[ ${#NOT_FOUND[@]} -gt 0 ]]; then
  echo "Not found / skipped:"
  for s in "${NOT_FOUND[@]}"; do
    echo "  - $s"
  done
fi

echo ""
echo "注意: ~/.harness-forge.state.json や生成された harness ファイルは手動削除してください。"
