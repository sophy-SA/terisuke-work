# harness-forge — Phase 9 packaging shortcuts
#
# Usage:
#   make install         — ~/.claude/skills/ に symlink で 3 skill を install
#   make install-copy    — symlink ではなく copy で install (repo 移動の影響を受けない)
#   make uninstall       — ~/.claude/skills/ から 3 skill を削除
#   make test            — E2E テストスイート (14 ケース) を実行
#   make verify          — install + test + uninstall の往復を 1 コマンドで
#   make clean           — tests/sandbox-* / harness-report.* / state ファイル削除
#   make help            — このヘルプを表示

.PHONY: help install install-copy uninstall test verify clean

REPO_ROOT := $(shell pwd)
SKILLS_DIR := $(HOME)/.claude/skills
SKILLS := harness-profiler harness-generator harness-validator harness-evolver

help:
	@echo "harness-forge — make targets:"
	@echo "  install        symlink で skills を install"
	@echo "  install-copy   copy で install"
	@echo "  uninstall      install を取り消す"
	@echo "  test           E2E テスト実行"
	@echo "  verify         install→test→uninstall の往復"
	@echo "  clean          sandbox / レポートファイル削除"

install:
	@bash $(REPO_ROOT)/install.sh

install-copy:
	@bash $(REPO_ROOT)/install.sh --copy

uninstall:
	@bash $(REPO_ROOT)/uninstall.sh

test:
	@bash $(REPO_ROOT)/tests/e2e.sh

verify: install test uninstall
	@echo "✓ verify (install + test + uninstall) 完了"

clean:
	@rm -rf $(REPO_ROOT)/tests/sandbox $(REPO_ROOT)/tests/sandbox-* 2>/dev/null || true
	@rm -f $(REPO_ROOT)/.harness-forge.state.json 2>/dev/null || true
	@rm -f $(REPO_ROOT)/harness-report.json $(REPO_ROOT)/harness-report.md 2>/dev/null || true
	@echo "✓ clean 完了"
