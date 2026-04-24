# Merge Strategy

既存ファイルと衝突した際の3つの統合モード。

## 1. `overwrite` (デフォルト)

対象パスが既存の場合:
1. 既存内容のハッシュを計算
2. state.json の `file_hashes[path]` と比較
   - ハッシュ一致 → 前回 generator が書いた内容。**上書き**
   - ハッシュ不一致 → ユーザーが編集した。**中断し`--force-overwrite <path>` を促す**
3. 存在しない場合はそのまま書き込み

新しいハッシュは state.json に記録。

## 2. `skip_if_exists`

対象パスが既存なら**何もしない** (既存を尊重)。
- `.git/hooks/pre-commit` — ユーザーの既存 git hook を破壊しない
- `CLAUDE.md` — 既存のプロジェクト記述を上書きしない
- `docs/harness.md` — 過去の harness-forge 実行による記述を尊重

存在しない場合のみ新規作成。

## 3. `json-deep`

`.claude/settings.json` 専用の deep merge。

### アルゴリズム

- 既存 JSON と生成 JSON を両方パース
- Object (dict) は再帰的にキーごとにマージ
- Array は**ユニオン + dedup** (特に `permissions.allow`, `permissions.deny`, `hooks.*.[].hooks`)
- Scalar (string/number/bool): **特殊ルール適用**
  - `hooks.*` 配下のエントリは**必ず追加** (既存 entry と生成 entry が matcher 一致 → 重複排除後に追加)
  - その他のキーは **既存優先** (ユーザー明示設定を尊重)

### 例

**既存:**
```json
{
  "permissions": {
    "allow": ["Bash(ls:*)"]
  },
  "theme": "dark"
}
```

**生成:**
```json
{
  "permissions": {
    "allow": ["Bash(ruff:*)", "Bash(black:*)"]
  },
  "hooks": {
    "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"command": "..."}]}]
  }
}
```

**merge 結果:**
```json
{
  "permissions": {
    "allow": ["Bash(black:*)", "Bash(ls:*)", "Bash(ruff:*)"]
  },
  "theme": "dark",
  "hooks": {
    "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"command": "..."}]}]
  }
}
```

### 重複排除ロジック

- `permissions.allow`: 文字列比較で完全一致を排除 (ソート)
- `permissions.deny`: 同上
- `hooks.<event>.[].matcher`: 同じ matcher を持つ entry は後から来るほう (生成側) が勝つ (ユーザーが matcher を変更した場合は unintended behavior なので warn)

### 競合時の挙動

- JSON パースエラー (既存ファイルが破損) → 中断、ユーザーに修正を促す
- schema 違反 → 中断、参考 URL を提示

---

## state.json の構造

`.harness-forge.state.json` に以下を記録:

```json
{
  "schema_version": "1.0",
  "generator_version": "0.1.0",
  "last_run_at": "2026-04-24T12:00:00Z",
  "profile_hash": "sha256:abc123...",
  "archetype_primary": "daily-utility",
  "files_written": [
    {
      "path": "CLAUDE.md",
      "merge": "skip_if_exists",
      "action": "created",
      "sha256_after": "..."
    },
    ...
  ],
  "file_hashes": {
    "CLAUDE.md": "sha256:...",
    ".claude/settings.json": "sha256:...",
    ...
  },
  "user_edits_detected": []
}
```

## `--force-overwrite` の挙動

- `--force-overwrite CLAUDE.md` → CLAUDE.md のユーザー編集を無視して上書き
- `--force-overwrite all` → 全ファイルで user_edits_detected を無視
- `--force-overwrite none` (default) → ユーザー編集があれば中断

## エッジケース

1. **シンボリックリンク**: `follow symlink = false`。target がシンボリックリンクなら警告して skip
2. **親ディレクトリが無い**: 自動作成 (mkdir -p)
3. **書き込み権限無し**: エラーで中断 (適切な `chmod` を案内)
4. **ファイルサイズ制限**: generator は 1MB を超える生成をしない (設定ミスの兆候)
