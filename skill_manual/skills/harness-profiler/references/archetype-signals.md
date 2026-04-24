# アーキタイプ判定ロジック

回答ベクトルから各アーキタイプのスコアを計算する方式を定義する。

実装は `scripts/detect_archetype.py` を参照。

---

## 入力

Profile.json の値 (未完成状態で OK、S1-S5 完了時点):

- `project.languages[]`
- `project.root_kind[]`
- `workflow.plan_work_review`
- `workflow.precommit_strictness`
- `quality_gates.required_checks[]`
- `quality_gates.ci_external`
- `safety.handles_secrets`

---

## 出力

```json
{
  "archetype_primary": "daily-utility",
  "archetype_scores": {
    "daily-utility": 0.72,
    "production-saas": 0.15,
    "ml-data": 0.08,
    "design-heavy": 0.05
  }
}
```

各スコアは 0.0〜1.0、合計は 1.0 に正規化。

---

## 判定信号とスコア寄与

### daily-utility

| 信号 | 寄与 |
|---|---|
| `root_kind` に `cli` 含む | +0.40 |
| `precommit_strictness` = `none` | +0.20 |
| `precommit_strictness` = `lint-only` | +0.15 |
| `ci_external` = false AND `required_checks` ⊆ {lint, format} | +0.20 |
| `handles_secrets` = false | +0.10 |
| `plan_work_review` = false | +0.10 |
| その他の root_kind がない (cli のみ) | +0.20 |

### production-saas

| 信号 | 寄与 |
|---|---|
| `root_kind` に `web` 含む | +0.40 |
| `required_checks` に `typecheck` AND `unit-test` 両方 | +0.25 |
| `required_checks` に `security-scan` | +0.15 |
| `handles_secrets` = true | +0.15 |
| `plan_work_review` = true | +0.10 |
| `ci_external` = false (scaffold 対象) | +0.05 |

### ml-data

| 信号 | 寄与 |
|---|---|
| `root_kind` に `notebook` 含む | +0.50 |
| 主要言語が `python` | +0.20 |
| `required_checks` に `integration-test` | +0.10 |
| `plan_work_review` = true | +0.10 |
| `handles_secrets` = true (データソース認証) | +0.10 |

### design-heavy

| 信号 | 寄与 |
|---|---|
| `root_kind` に `design` 含む | +0.45 |
| `required_checks` に `a11y` | +0.20 |
| `required_checks` に `visual-regression` | +0.20 |
| `specialized_reviewers` に `ui` または `a11y` | +0.10 |
| 主要言語が TypeScript/JavaScript | +0.05 |

---

## 正規化と同点処理

1. 各アーキタイプで生スコアを集計
2. 合計を計算、`sum > 0` なら各スコアを `sum` で割る (正規化)
3. `sum == 0` の場合 (全信号ゼロ) は `daily-utility` = 1.0 でデフォルト
4. トップ2スコアの差が 0.15 未満 → "Mixed" と判断し、ユーザーに override プロンプト必須
5. `archetype_primary` はトップ1をデフォルト、ユーザー確認後に確定

---

## オーバーライドポリシー

ユーザーは `archetype_primary` を手動で override できる:

```
判定結果:
  daily-utility: 0.72  ← デフォルト採用
  production-saas: 0.15
  ml-data: 0.08
  design-heavy: 0.05

このままでいいですか? (yes / 別のアーキタイプを選ぶ / 詳細を見る)
```

override 時、`archetype_scores` はそのまま保持 (監査ログとして)。

---

## Mixed ケースの扱い (MVP)

MVP では Mixed を**許容しない**。トップ1を強制採用。将来:
- Phase 8+ で `archetype_primary` + `archetype_secondary` を導入し、template を2段合成する案
- または "mixed" archetype を別途作り、extends で複合化する案

---

## テストケース (scripts/detect_archetype.py のテスト目標)

| # | 入力ハイライト | 期待 primary | 許容スコア範囲 |
|---|---|---|---|
| 1 | root_kind=[cli], precommit=lint-only, no CI | daily-utility | >0.60 |
| 2 | root_kind=[web], required_checks=[typecheck,unit-test], handles_secrets | production-saas | >0.55 |
| 3 | root_kind=[notebook], languages=[python] | ml-data | >0.55 |
| 4 | root_kind=[design], required_checks=[a11y,visual-regression] | design-heavy | >0.60 |
| 5 | 全信号ゼロ (empty) | daily-utility | 1.0 (default) |
| 6 | root_kind=[cli, web] 両方 | 最高スコアのほう | 差が 0.15 以内なら mixed 警告 |
