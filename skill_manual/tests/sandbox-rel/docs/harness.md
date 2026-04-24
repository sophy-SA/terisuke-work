# このプロジェクトの Claude Code ハーネス

**生成元**: harness-forge (archetype: daily-utility)
**生成日**: 実行時刻を埋め込む予定

## 何が scaffold されたか

このディレクトリに以下のファイルが配置されました:

| ファイル | 役割 |
|---|---|
| `CLAUDE.md` | セッション開始時の作業ルール (50行以内ポインタ主義) |
| `.claude/subagents/reviewer.md` | 差分レビュー専用の read-only subagent |
| `.claude/hooks/post-edit-format.sh` | Edit/Write 後に対象ファイルを自動整形する PostToolUse hook |
| `.claude/hooks/pre-commit-lint.sh` | git pre-commit 本体。staged ファイルのみに lint を実行 |
| `.claude/settings.json` | permissions (read-only + formatter/linter 許可) + hook 登録 |
| `.git/hooks/pre-commit` | `.claude/hooks/pre-commit-lint.sh` を呼ぶ薄いラッパ (既存があれば skip) |

## なぜこの構成か

### archetype: daily-utility の思想

個人用 CLI / shell script / 日常ツールでは、**重厚な harness は過剰**です。以下を最小セットとしました:

1. **速い自動整形** (PostToolUse hook, ミリ秒応答) — 編集のたびにフォーマッタが走る
2. **commit 時の lint ゲート** (pre-commit, 秒応答) — 壊れたコードを commit させない
3. **単一 read-only reviewer** — 変更後に必ず目を通すチェックポイント

### 採用しなかった要素 (意図的)

- **CI/CD 自動生成**: 個人ツールでは GitHub Actions を強制しない。必要なら production-saas archetype で再生成してください
- **専門化 reviewer チーム**: security / performance / a11y reviewer は過剰。必要になったら `/harness-profiler` を production-saas で再実行して増築
- **長いコーディングルール集**: CLAUDE.md を 200 行の規約集にしない。ルールが守られないなら hook に変換する

## 増築するには

将来プロジェクトが商用規模に成長したら:

1. `profile.json` を編集して `archetype_primary` を `production-saas` に変更
2. `quality_gates.required_checks` に `typecheck`, `unit-test`, `security-scan` を追加
3. `/harness-generator` を再実行

Generator が差分のみ適用し、既存のユーザー編集ファイルは保護されます。

## 検証

scaffold 直後、以下で健全性を確認できます:

```bash
# Validator を実行
/harness-validator
```

`harness-report.md` に結果が出力されます。errors が 0 であれば harness は健全です。

## 参考資料

- Anthropic 公式: [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Anthropic 公式: [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- Sakasegawa: [Harness Engineering 2026](https://nyosegawa.com/en/posts/harness-engineering-best-practices-2026/)
- HumanLayer: [Skill Issue: Harness Engineering for Coding Agents](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents)
