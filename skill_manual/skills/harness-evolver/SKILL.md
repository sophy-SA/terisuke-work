---
name: harness-evolver
description: |
  既存の harness-forge scaffold (CLAUDE.md / .claude/* / docs/harness.md) を、最新の archetype
  template と照合し drift を検出。template の更新内容を選択的に既存 harness へ反映する
  read-only-by-default skill。
  Use when: archetype を更新した後 / 月次の harness メンテナンス / `.harness-forge.state.json`
  と現状ファイルが食い違った時。Do NOT use for: 新規 scaffold (harness-generator),
  整合性チェック (harness-validator), profile 再判定 (harness-profiler).
---

# harness-evolver

既存 harness と最新 archetype template の **3-way drift 検出 + 選択的反映** を行う。

## 前提

対象プロジェクトに以下が必要:
- `.harness-forge.state.json` (harness-generator が生成)
- `profile.json` (harness-profiler が生成)
- harness-forge repo (assets/archetypes + assets/templates にアクセス可能)

## Step 1: drift 検出 (read-only)

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/evolve.py" \
  --profile ./profile.json \
  --state ./.harness-forge.state.json \
  --dry-run
```

### 出力カテゴリ

| カテゴリ | 意味 | デフォルト挙動 |
|---|---|---|
| `unchanged` | template も file も state 時点から変化なし | スキップ |
| `template_updated_safe` | template 更新あり / user 未編集 → 安全に上書き可 | `--apply` で反映 |
| `template_updated_conflict` | template 更新あり / user 編集あり → 衝突 | スキップ (要手動) |
| `user_edited_only` | template 不変 / user 編集あり | スキップ (尊重) |
| `user_deleted` | state に記録あるが現在 file 存在せず | スキップ (warn) |
| `new_template_file` | archetype に追加された (state に未記録) | `--apply` で追加 |
| `removed_template_file` | state にあるが archetype から削除された | スキップ (warn) |

## Step 2: 反映 (`--apply`)

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/evolve.py" \
  --profile ./profile.json \
  --state ./.harness-forge.state.json \
  --apply
```

- `template_updated_safe` + `new_template_file` のみ反映
- `template_updated_conflict` は **`.evolved-conflict.md` を生成して提示**
- state.json を更新 (新しい hash / `last_run_at`)
- `.harness-forge.evolution.log` に履歴追記

## Step 3: 衝突手当て

`--apply` 後に `.evolved-conflict.md` がある場合、ユーザーが手動でマージ:
- 旧 template (state 時点) / 新 template (現在) / user 編集版 の 3-way diff を提示
- マージ後 `git add <file>` して次回 `evolve --apply` で warn が消える

## 強制反映 (`--force`)

```bash
python3 evolve.py --apply --force
```

`template_updated_conflict` も template 側に強制上書き。**user 編集を破棄するため非推奨**。

## 採用しなかった機能 (意図的)

- **profile.json 自動再判定** — profiler を別途呼んで再生成すべき
- **archetype 切替** — 別 skill (`harness-migrator`, 将来) で扱う
- **3-way 自動マージ** — `git merge-file` 相当は controversy が大きい。conflict は人間判断に委ねる
- **history rewrite** — state.json の過去の `last_run_at` 等は変更しない

## Validator との関係

- harness-evolver は generator の差分版
- 反映後は `/harness-validator` を実行して C04/C05/C07 等の整合性を確認することを案内する

## 出力

stdout に sections:
- `## Summary` — 各カテゴリの件数
- `## Files` — file ごとの category + 推奨アクション
- `## Next steps` — `--apply` するか / `/harness-validator` 実行するか
