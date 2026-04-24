# アーキテクチャ

## 3-skill family のデータフロー

```
┌─────────────────┐    profile.json     ┌───────────────────┐    scaffold files    ┌──────────────────┐
│ harness-profiler│ ──────────────────► │ harness-generator │ ──────────────────►  │ harness-validator│
│  (インタビュー)   │                    │  (実ファイル生成)  │                     │   (整合性検査)   │
└─────────────────┘                     └───────────────────┘                      └──────────────────┘
         ▲                                        │                                         │
         │                                        ▼                                         ▼
   ユーザー回答                              CLAUDE.md, .claude/*,                     harness-report.{json,md}
                                          docs/harness.md, CI yml,
                                          .harness-forge.state.json
```

## 設計原則

1. **Skills 間の自動チェーンなし** — ユーザーが明示的に3つのコマンドを順に呼ぶ。各 Skill は最後に次のコマンドを提案する。
2. **`profile.json` を単一情報源に** — Generator と Validator は再インタビューしない。編集可能で re-runnable。
3. **Template は plain `{{VAR}}` 置換 + `{{#if}}` ブロック** — Jinja 等の外部依存を持たない（stdlib Python のみ）。
4. **Validator は read-only** — 自動修正せず、report のみ返す。

## 中間成果物

### `profile.json` (Profiler → Generator)

- 配置: 対象プロジェクトの cwd
- スキーマ: `assets/knowledge/schema/profile.schema.json` (v1.0)
- 主要フィールド:
  - `project.{name, languages, root_kind}` — プロジェクト属性
  - `archetype_primary` + `archetype_scores` — アーキタイプ判定
  - `workflow.{plan_work_review, precommit_strictness, long_running_agents}` — ワークフロー方針
  - `quality_gates.{required_checks, ci_external}` — 品質ゲート
  - `review.{ai_second_opinion, specialized_reviewers}` — レビュー体制
  - `safety.{handles_secrets, destructive_ops}` — セキュリティ要件
  - `meta.{locale, existing_claude_dir, intents}` — メタ情報
  - `overrides` — ユーザー手動調整

### `.harness-forge.state.json` (Generator が記録)

- 配置: 対象プロジェクトの cwd（gitignore）
- 内容: `profile_hash` / `generator_version` / `files_written[]` / `user_edits_detected[]`
- 用途: 再実行時の no-op 判定、ユーザー編集ファイルの保護

### `harness-report.{json,md}` (Validator が出力)

- 配置: 対象プロジェクトの cwd
- スキーマ: `assets/knowledge/schema/report.schema.json` (v1.0)
- 内容: `summary.{errors, warnings, info}` + `issues[]` (id / severity / file / line / fix_hint)

## Archetype 設計

4つの archetype を YAML で定義 (`assets/archetypes/*.yaml`):

| Archetype | MVP | 特徴 |
|---|---|---|
| `daily-utility` | ✅ | 個人用 CLI、最小 harness、PostToolUse format + pre-commit lint |
| `production-saas` | 計画 | 商用 SaaS、Plan→Work→Review、全層品質ゲート |
| `ml-data` | 計画 | ML パイプライン、データ妥当性検証、大容量 artifact ブロック |
| `design-heavy` | 計画 | UI/UX 重視、a11y レビュー、スクリーンショット差分 |

Archetype YAML は `extends:` でコンポジション可能（production-saas extends daily-utility 等）。

## テンプレートシステム

`assets/templates/<archetype>/` 配下に、拡張子 `.tmpl` のテンプレートファイルを配置。

**変数**: `{{PROJECT_NAME}}`, `{{LOCALE}}`, `{{PRECOMMIT_STRICTNESS}}`, etc.
**条件分岐**: `{{#if HANDLES_SECRETS}}...{{/if}}`

Archetype YAML の `templates:` リストが `src` → `dest` のマッピングを宣言:

```yaml
templates:
  - src: daily-utility/CLAUDE.md.tmpl
    dest: CLAUDE.md
  - src: daily-utility/hooks/pre-commit-lint.sh.tmpl
    dest: .claude/hooks/pre-commit-lint.sh
    mode: "0755"
  - src: daily-utility/settings.patch.json.tmpl
    dest: .claude/settings.json
    merge: json-deep
```

## Merge 戦略

既存プロジェクト（`meta.existing_claude_dir=true`）では3種のマージモード:

- `overwrite` — デフォルト。既存内容が異なれば `--force` 必須
- `skip_if_exists` — ユーザーが既に持っているファイルを保護 (`.git/hooks/pre-commit`, 既存 `CLAUDE.md`)
- `json-deep` — `.claude/settings.json` 専用。`hooks.*` は union、他は既存優先

## 既存アセットとの関係

- **`skill-creator` skill** — Skill 作成時の frontmatter/構造参照。Generator はチェーンせず、ヒントとして言及
- **Anthropic 公式ドキュメント** — `assets/knowledge/anthropic-official.md` に distilled
- **コミュニティパターン** — `assets/knowledge/community-patterns.md` に distilled

## Out of scope

- Cursor / Windsurf / Aider 等、Claude Code 以外のエージェントツール用設定生成
- GUI / Web インターフェース
- 自動 harness アップデート（既存 harness の進化は将来の `harness-evolver` で検討）
- チーム共有ワークフロー（`.harness-forge.state.json` の commit 戦略）
