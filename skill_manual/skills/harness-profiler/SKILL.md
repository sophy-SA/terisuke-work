---
name: harness-profiler
description: |
  ユーザーにインタビューしてプロジェクト属性を聞き取り、profile.json を出力する skill。
  Claude Code の harness (CLAUDE.md / subagents / hooks / skills / validation workflow)
  を設計するための中間成果物を生成する。
  Use when the user says "harness を設計して", "新規プロジェクトの Claude Code 設定を作って",
  "design my Claude Code harness", "profile.json を作って". 常に harness-generator の**前に**
  実行する。
  Do NOT use for: editing an existing settings.json (use update-config skill instead),
  adding a single hook (use update-config), creating a single skill (use skill-creator),
  tuning permissions only (use fewer-permission-prompts), running scaffolding without
  interview (invoke harness-generator directly with existing profile.json).
allowed-tools: Read, Write, Bash(python3:*), Bash(ls:*), Bash(cat:*), Bash(pwd:*), Bash(git status:*), Bash(git log:*), Bash(find:*), Bash(grep:*)
---

# harness-profiler

**役割**: 2〜3分のインタビューでプロジェクト属性を聞き取り、harness-generator が消費する `profile.json` を作成する。

## 起動時チェックリスト

```
- [ ] Step 1: cwd を確認 (pwd) — 対象プロジェクトにいるか
- [ ] Step 2: 既存 profile.json の有無確認
- [ ] Step 3: プロジェクト推定情報の収集 (README, package.json, pyproject.toml 等)
- [ ] Step 4: S1-S6 のインタビュー (AskUserQuestion 使用)
- [ ] Step 5: アーキタイプ判定 (detect_archetype.py)
- [ ] Step 6: profile.json を書き出し (write_profile.py)
- [ ] Step 7: 結果サマリーを提示 + 次アクションを案内
```

## Step 1: cwd と対象プロジェクト確認

まず `pwd` と `ls` を実行して現在地を確認する。`~/.claude/` や harness-forge の repo 内で起動された場合は、**対象プロジェクトに cd してから再実行してください**と警告して終了する。

## Step 2: 既存 profile.json の確認

```bash
ls profile.json 2>/dev/null
```

存在する場合、ユーザーに確認:
- 上書きしますか？
- 編集モードに入りますか？ (既存値をプレフィルしてインタビュー)
- そのまま harness-generator を呼ぶ場合はこの skill は不要と案内

## Step 3: プロジェクト推定情報の収集

以下を軽く調べ、インタビューのプレフィル値にする (重い探索はしない):

- `README.md` / `README.rst` の最初の5行
- `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Gemfile` の有無 → 言語推定
- `.git/` の有無
- `.claude/` ディレクトリの有無 → `meta.existing_claude_dir` の初期値

**注意**: 探索は1層のみ。`find -maxdepth 2` を超えない。プロジェクトが巨大な場合の context 汚染を避ける。

## Step 4: インタビュー (S1-S6)

詳細な質問バンクは [references/interview-script.md](references/interview-script.md) を参照。

各セクションは `AskUserQuestion` ツールで質問する。原則:
- 1セクションあたり最大4問まで
- 選択肢はMVP では 2-4 個、自由記述は避ける (summary / intents のみ free-form)
- 前の回答が次セクションに影響する場合は分岐を明示

### セクション構造

| # | セクション | 必須 | 質問数 |
|---|---|---|---|
| **S1** | Project Shape | ✅ | 3 (目的・言語・構造) |
| **S2** | Workflow Preferences | ✅ | 2-3 |
| **S3** | Quality Gates | ✅ | 2 |
| **S4** | Review & Collaboration | | 1-2 (S3 からの自動推奨を確認) |
| **S5** | Secrets & Safety | | 2 |
| **S6** | Meta | ✅ | 3 (locale, existing_claude_dir, intents) |

**MVP 動作**: S1 と S6 のみ必須。S2-S5 は`--quick` モード時スキップ (デフォルト値を使用)。

### 質問フォーマット例 (S1.1)

```
Q1.1 このプロジェクトの目的を1-2文で教えてください (free-form)
  → 回答は project.summary に格納
```

```
Q1.2 主要言語は? (複数選択可)
  [ ] Python
  [ ] TypeScript / JavaScript
  [ ] Go
  [ ] Rust
  [ ] Swift / Kotlin
  [ ] その他 (自由記述)
```

```
Q1.3 プロジェクトの主構造は? (上位2つ)
  [ ] CLI / daily utility / shell script
  [ ] Web / SaaS backend or frontend
  [ ] ML / data analysis / notebook
  [ ] Design-heavy UI / デザインシステム
  [ ] Mixed (複数に該当)
```

## Step 5: アーキタイプ判定

`scripts/detect_archetype.py` を実行し、S1-S5 の回答から各アーキタイプスコア (0.0〜1.0) を計算する。

判定ロジックは [references/archetype-signals.md](references/archetype-signals.md) に詳述。概要:

| アーキタイプ | 判定信号 |
|---|---|
| `daily-utility` | root_kind ⊇ [cli] AND precommit_strictness ∈ {none, lint-only} AND !ci_external |
| `production-saas` | root_kind ⊇ [web] AND required_checks ⊇ [typecheck, unit-test] AND handles_secrets |
| `ml-data` | primary_language = python AND root_kind ⊇ [notebook] |
| `design-heavy` | root_kind ⊇ [design] AND (required_checks ⊇ [a11y] OR [visual-regression]) |

**ユーザー確認**: 計算結果 (スコアベクタ) を提示し、`archetype_primary` をユーザーが承認または override できるようにする。

## Step 6: profile.json の書き出し

`scripts/write_profile.py` に全回答を渡して実行:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/write_profile.py" --output ./profile.json
```

asset path (schema) は自動解決されます。スクリプトは以下を実行:
1. 回答を profile schema (v1.0) にマップ
2. `assets/knowledge/schema/profile.schema.json` で検証
3. エラーがあれば修正を促す (再質問 or abort)
4. 成功したら `./profile.json` に書き出し
5. 最終サマリーを stdout に diff 可能な table で表示

## Step 7: ユーザーへの案内

最後に以下を表示して完了:

```
✓ profile.json を作成しました (./profile.json)

次のステップ:
  1. profile.json の内容を確認 (cat profile.json)
  2. 必要なら手動で編集 (フィールド定義: references/profile-schema.md)
  3. harness-generator を実行:
     /harness-generator

注意:
  - profile.json を編集してから再度 profiler を実行する必要はありません
  - 編集後に直接 generator を呼んで OK (同じ profile ベースで再 scaffold)
```

## --batch モード (E2E テスト用)

```
/harness-profiler --batch answers.yaml
```

`answers.yaml` に全回答が記載されている場合、インタビューをスキップして直接 profile.json を生成。
fixture テスト (tests/e2e.sh) で使用。

answers.yaml のフォーマット例は [references/interview-script.md](references/interview-script.md) を参照。

## 禁止事項

- 4 問を超える質問を1セクションで出さない (ユーザー疲労)
- S2-S5 で自由記述を強制しない (summary / intents のみ free-form)
- 既存 profile.json を黙って上書きしない
- 対象プロジェクト以外の cwd (`~/.claude/` 等) で実行しない
- profile の schema 検証エラーを握りつぶさない

## 参照ファイル

- [references/interview-script.md](references/interview-script.md) — 全質問バンク + 分岐ロジック
- [references/archetype-signals.md](references/archetype-signals.md) — 回答 → アーキタイプスコア計算詳細
- [references/profile-schema.md](references/profile-schema.md) — profile.json の人間可読スキーマ
- `../../assets/knowledge/schema/profile.schema.json` — JSON Schema 本体
