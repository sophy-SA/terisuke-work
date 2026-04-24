---
name: harness-generator
description: |
  profile.json を読み込み、Claude Code の harness 一式 (CLAUDE.md, .claude/subagents/,
  .claude/hooks/, .claude/settings.json, docs/harness.md, git pre-commit) を実ファイル
  として scaffold する skill。archetype ごとに最適化された template set を適用する。
  Use when the user says "harness を生成して", "scaffold my CLAUDE.md", "profile から
  ハーネス作って", "generate harness". harness-profiler が作成した profile.json が
  存在する前提で動作する。
  Do NOT use without profile.json (先に harness-profiler を実行), for single-file
  edits to existing harness (update-config skill を使う), creating individual skills
  (skill-creator を使う), or re-interviewing the user (harness-profiler がその役割).
allowed-tools: Read, Write, Edit, Bash(python3:*), Bash(ls:*), Bash(cat:*), Bash(pwd:*), Bash(chmod:*), Bash(mkdir:*), Bash(cp:*)
---

# harness-generator

**役割**: `./profile.json` を単一情報源とし、archetype に対応する template set から実ファイルを scaffold する。

## 起動時チェックリスト

```
- [ ] Step 1: cwd に profile.json が存在することを確認
- [ ] Step 2: profile.json をスキーマ検証
- [ ] Step 3: archetype_primary から template set を決定
- [ ] Step 4: 既存 .harness-forge.state.json を確認 (再実行判定)
- [ ] Step 5: apply_scaffold.py を実行してファイル生成
- [ ] Step 6: ユーザーに結果サマリー + 次アクション案内
```

## Step 1: profile.json の存在確認

```bash
ls profile.json 2>/dev/null
```

無ければ:
```
エラー: ./profile.json が見つかりません。
先に harness-profiler を実行してください:
  /harness-profiler
```

## Step 2: スキーマ検証

`scripts/apply_scaffold.py` の冒頭で JSON Schema 検証。エラー時は詳細を表示して終了。

## Step 3: archetype 判定と template set ロード

`profile.archetype_primary` を読み、`assets/archetypes/<archetype>.yaml` をロードする。
`extends:` があれば再帰的に親の templates も含める。

現在 MVP 対応:
- `daily-utility` — 完全実装
- `production-saas` / `ml-data` / `design-heavy` — stub (`status: planned`)。呼ばれたら警告して
  "MVP では daily-utility のみサポート。profile.archetype_primary を変更してください" と案内。

## Step 4: 再実行判定

既に `./.harness-forge.state.json` がある場合:
- `profile_hash` が同じ → **no-op** (差分なし) と案内
- `profile_hash` が異なる → 差分 scaffold (ユーザー編集ファイルは保護)

ユーザー編集検出: state.json の `file_hashes[path]` と現在ファイルの SHA-256 比較。

## Step 5: apply_scaffold.py の実行

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/apply_scaffold.py" --profile ./profile.json
```

asset path は自動解決されます (install.sh 経由 symlink install なら何もせずとも動作)。repo を移動した場合は `HARNESS_FORGE_ASSETS` 環境変数を設定:

```bash
export HARNESS_FORGE_ASSETS=/path/to/harness-forge/assets
```

スクリプトは以下を実行:
1. profile.json 読み + schema 検証
2. archetype YAML 読み (extends 解決)
3. 変数 flatten (profile → `{PROJECT_NAME: ..., LOCALE: ..., ...}`)
4. 各 template について:
   - 読み込み → `{{VAR}}` 置換 + `{{#if VAR}}` ブロック評価
   - dest パス解決
   - merge mode 適用 (`overwrite` / `skip_if_exists` / `json-deep`)
   - 必要なら `chmod` で mode 設定
5. conditional_templates を filter (条件評価) して同じく適用
6. `.harness-forge.state.json` に記録

詳細は [references/template-index.md](references/template-index.md) と
[references/merge-strategy.md](references/merge-strategy.md) を参照。

## Step 6: 結果サマリー

生成成功時:
```
✓ harness を生成しました (archetype: daily-utility)

生成ファイル:
  + CLAUDE.md                         (35 lines)
  + .claude/subagents/reviewer.md
  + .claude/hooks/post-edit-format.sh (mode 0755)
  + .claude/hooks/pre-commit-lint.sh  (mode 0755)
  + .claude/settings.json              (merged)
  + .git/hooks/pre-commit              (skipped — already exists)
  + docs/harness.md

次のステップ:
  1. harness-validator を実行して整合性確認:
     /harness-validator
  2. .claude/hooks/post-edit-format.sh の動作を確認 (適当なファイルを編集)
  3. 不足しているツール (ruff / biome 等) をインストール
```

## --force-overwrite オプション

ユーザー編集が検出されたファイルを強制上書きしたい場合:

```
/harness-generator --force-overwrite CLAUDE.md
```

複数指定可。`--force-overwrite all` で全て強制上書き (通常は推奨しない)。

## 禁止事項

- profile.json 無しで動作しない (エラーで終了)
- `.git/hooks/pre-commit` が既存なら絶対に上書きしない (skip_if_exists)
- `.claude/settings.json` の merge で既存 `permissions.deny` を勝手に削除しない
- profile の schema 検証を skip しない
- ユーザー編集が検出されたファイルを `--force-overwrite` 無しで上書きしない
- scaffold 実行中に skill-creator や他 skill を invoke しない (hint 表示のみ)

## 参照ファイル

- [references/template-index.md](references/template-index.md) — archetype ごとの template 一覧
- [references/merge-strategy.md](references/merge-strategy.md) — 3 種類の merge mode 詳細
- [references/hook-catalog.md](references/hook-catalog.md) — 利用可能な hook テンプレート一覧
- `../../assets/archetypes/*.yaml` — archetype 定義
- `../../assets/templates/` — テンプレート本体
- `../../assets/knowledge/schema/profile.schema.json` — profile.json 検証スキーマ
