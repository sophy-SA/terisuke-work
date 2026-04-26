# User Guide: harness-forge 詳細マニュアル

このドキュメントは [tutorial.md](./tutorial.md) を読み終えた人向けの**詳細リファレンス**です。
各 skill のオプション、profile.json の編集、衝突解決、バックアップ戦略、よくある落とし穴を網羅します。

---

## インストールモード

### symlink (デフォルト)

```bash
make install
```

- repo 側の更新が即座に反映される
- repo を移動 (`mv ~/harness-forge ~/work/harness-forge`) すると symlink が壊れる → 再 install
- 推奨: 個人 dev 環境

### copy

```bash
make install-copy
# または
bash install.sh --copy
```

- repo の場所に依存しない
- repo 更新時は再 install が必要
- 推奨: CI / 共有環境 / repo を消したい人

### `HARNESS_FORGE_ASSETS` 環境変数

scripts は assets を以下の順で探します:

1. `--archetypes-dir` / `--templates-dir` / `--schema` 引数 (明示)
2. `HARNESS_FORGE_ASSETS` 環境変数
3. script 自身の location からの相対 (symlink install ならこれで解決)

repo を移動する人向けの設定:

```bash
echo 'export HARNESS_FORGE_ASSETS=/path/to/harness-forge/assets' >> ~/.bashrc
```

---

## profile.json: 編集できる項目

profiler が出力した後でも、以下のフィールドは**直接編集して generator を再実行**できます。

### 安全に変えられる

| フィールド | 例 | 効果 |
|---|---|---|
| `meta.intents` | `["lint 厳格化", "テスト先行"]` | CLAUDE.md の "プロジェクト固有" 節に反映 |
| `workflow.precommit_strictness` | `"lint-test"` → `"full"` | pre-commit-lint hook の動作変化 |
| `safety.handles_secrets` | `false` → `true` | `block-secret-commit.sh` が追加される |
| `safety.destructive_ops` | `["rm-rf", "deploy"]` | 該当する block hook が追加される |
| `review.specialized_reviewers` | `["security"]` を追加 | (production-saas のみ) 該当 reviewer が active 化 |

### 慎重に変える (再 scaffold が必要)

| フィールド | 注意 |
|---|---|
| `archetype_primary` | `daily-utility` → `production-saas` 等は **template が大きく変わる** ため、可能なら別ディレクトリで試してから |
| `project.languages` | language 別の許可コマンドが変わる (settings.json の Bash allow が再生成される) |
| `meta.locale` | MVP では `ja` のみ実装 (将来の拡張のため schema にあるが未使用) |
| `meta.existing_claude_dir` | merge mode の挙動を変える。手動編集は非推奨 (generator が自動判定する) |

### 編集後の generator 挙動

```bash
# profile.json 編集後
/harness-generator

# 同じ profile_hash → "変化なし" と表示されて no-op
# 異なれば差分のみ scaffold:
#   - skip_if_exists ファイルは保護
#   - overwrite ファイルは新内容で上書き (ただし state hash と現在 hash が一致するもののみ)
#   - user 編集を検知したファイルは skip + 警告
```

---

## 既存プロジェクトへの導入 (merge mode)

既に `CLAUDE.md` や `.claude/settings.json` があるプロジェクトで harness-forge を走らせる場合:

| 既存ファイル | merge 挙動 |
|---|---|
| `CLAUDE.md` | **skip_if_exists** — 触らない。生成内容を見たければ別パスに `--output` (将来機能) または手動マージ |
| `.claude/subagents/*.md` | **overwrite** — 同名 subagent があれば上書き。バックアップ推奨 |
| `.claude/hooks/*.sh` | **overwrite** — 同上 |
| `.claude/settings.json` | **JSON deep-merge** — `permissions.allow` は配列 union、`hooks.PreToolUse[]` も union。既存 `theme` 等の設定値は保持 |
| `.git/hooks/pre-commit` | **skip_if_exists** — 既存があれば触らない (ユーザーの husky / lefthook 設定を破壊しないため) |
| `docs/harness.md` | **skip_if_exists** — 既存ドキュメントを尊重 |

### 推奨ワークフロー

```bash
# 1. 既存 CLAUDE.md と settings.json をバックアップ
cp CLAUDE.md CLAUDE.md.bak
cp .claude/settings.json .claude/settings.json.bak

# 2. scaffold
/harness-generator

# 3. 差分確認
diff CLAUDE.md.bak CLAUDE.md  # skip_if_exists なら何も変化していないはず
diff .claude/settings.json.bak .claude/settings.json  # union 結果

# 4. validator で整合性確認
/harness-validator
```

---

## 再実行 (idempotency) と user 編集の保護

`apply_scaffold.py` は `.harness-forge.state.json` で各 scaffolded ファイルの hash を記録します。
再実行時に以下を判定:

| 状態 | 挙動 |
|---|---|
| state hash == 現在 hash (user 未編集) | 新 template で上書き |
| state hash != 現在 hash (user 編集あり) | **skip + 警告** (上書きしない) |
| state に無く disk にあるファイル | template と一致しなければ user 作成と判断 (触らない) |

これは `harness-evolver` の drift 検出ロジックと同じ思想です。

---

## harness-evolver の使い方 (drift 反映)

### いつ使うか

- **自分で archetype yaml や template を更新した後**
- **harness-forge 側で新 hook が追加された後** (`git pull` してから)
- **scaffold から数ヶ月経って、現状と乖離していないか定期チェック**

### 基本フロー

```bash
# まず dry-run で drift 報告のみ
/harness-evolver

# 何が出るか:
#   - unchanged: 5
#   - template_updated_safe: 2     ← 自動反映可能
#   - user_edited_only: 1          ← user 尊重、skip
#   - template_updated_conflict: 1 ← 衝突、要手動
#   - new_template_file: 1         ← 新規追加可能
#   - removed_template_file: 0     ← deprecated だがファイルは残す

# 反映する場合
python3 ~/harness-forge/skills/harness-evolver/scripts/evolve.py \
  --profile ./profile.json --apply
```

### 衝突 (`.evolved-conflict.md`) の対処

`--apply` で skip された conflict は `.evolved-conflict.md` に記録されます:

```markdown
## `.claude/settings.json`
- 前回 scaffold 時 hash: sha256:abc...
- 現在 disk hash:        sha256:def...
- 期待 (新 template) hash: sha256:ghi...
```

対処手順:
1. 現在の disk file をバックアップ (`cp file file.bak`)
2. `git diff` で user 編集内容を確認
3. 新 template の内容を確認 (repo の `assets/templates/<archetype>/...`)
4. **手動で 3-way merge** (vim diff / VSCode merge editor 等)
5. マージ後 `git add <file>` → `evolve.py --apply` 再実行 → conflict が消えれば OK

> **`--force` を使うのは最終手段**。user 編集が破棄されます。

---

## バックアップ戦略

### 推奨: 一切手動で git に頼る

scaffold する前に必ず `git commit` 済み状態で開始。何かあっても `git checkout .` で戻せる。

```bash
git status          # working tree clean を確認
/harness-generator  # scaffold
git status          # 何が増えたか / 変わったかを確認
git add -p          # 部分的に add してチェック
```

### 避けるべきパターン

- `cd` 忘れて home dir で `/harness-generator` (cwd に scaffold される)
- 既存 CI 設定がある repo で `.github/workflows/ci.yml` を上書き (`production-saas` archetype は `skip_if_exists` だが念のため確認)
- `--force` を反射的に使う (user 編集破棄)

---

## Validator のシビアリティポリシー

| Severity | 意味 | merge gate |
|---|---|---|
| ERROR | scaffold が動作しない / セキュリティリスク | merge ブロック対象 |
| WARNING | 設計逸脱 / 将来の問題予兆 | 警告だが merge 可 |
| INFO | 改善余地 | 参考情報 |

主要チェック:

| ID | 内容 | Severity |
|---|---|---|
| C01 | CLAUDE.md ≤ 50 行 | WARN |
| C02 | CLAUDE.md ≤ 2000 tokens 相当 | WARN |
| C04 | settings.json 参照の hook script が実在 | **ERROR** |
| C05 | hook matcher 衝突 | WARN |
| C07 | subagent tools allowlist が既知ツールのみ | **ERROR** |
| C08 | CLAUDE.md 参照の subagent が実在 | **ERROR** |
| C10 | settings.json に secrets 漏洩なし | **ERROR** |
| C12 | settings.json が schema 準拠 | **ERROR** |
| C13 | handles_secrets=true なら secret-block hook 必須 | WARN |

---

## よくある落とし穴

### 1. linter が install されていない

scaffold された `pre-commit-lint.sh` は ruff / eslint / gofmt 等を **検出して呼ぶだけ**。
本体は別途 install:

```bash
# Python
pip install ruff black

# JS / TS
npm i -D eslint prettier biome

# Go
# (gofmt は標準同梱)
```

### 2. settings.json の "PreToolUse" 配列に重複 hook

`json-deep` merge は同名 hook を重複追加することがある (matcher 配列の union)。
`harness-validator` の C05 で警告される。手動で重複削除するか、`/harness-evolver --apply --force` で再生成。

### 3. profile.json を消してしまった

generator が再実行できない。`/harness-profiler` で再作成、または既存の
`.harness-forge.state.json` から `archetype_primary` を確認して minimum profile を手書き
(README に minimum example あり)。

### 4. `meta.existing_claude_dir` の自動判定

generator は `.claude/` の存在で判定。**手動で true/false を書き換えても無視される**ことがある。
既存挙動を変えたい場合は `--force-merge-mode overwrite` (将来機能) ではなく、対象ファイルを削除してから再 scaffold。

### 5. WSL / Windows で symlink install が効かない

Windows 環境では symlink 作成に admin 権限が必要なケースがある:

```bash
make install-copy   # symlink ではなく copy で install
```

### 6. CLAUDE.md が肥大化する

generator は 50 行以下で生成しますが、user が `intents` を 10 個書いたり、追加 hook の説明を CLAUDE.md に書き足してしまうとすぐ超える。原則:
- **詳細ルールは hook で機械強制** (CLAUDE.md には書かない)
- **アーキタイプ説明は `docs/harness.md` に外出し**
- C01 WARN が出たら CLAUDE.md を読み直してポインタに変換

---

## 環境変数一覧

| 変数 | 用途 | 既定 |
|---|---|---|
| `HARNESS_FORGE_ASSETS` | assets dir 明示 | (script location から解決) |
| `BLOCK_LARGE_ARTIFACT_MB` | ml-data archetype の hook 閾値 | 50 |
| `SKIP_LINTER_CONFIG_PROTECTION` | production-saas hook の一時 bypass | unset |
| `SKIP_PRE_PR_GATE` | production-saas hook の一時 bypass | unset |
| `HARNESS_FORGE_SKIP_INSTALL_TEST` | E2E Test 15 をスキップ (CI 等) | 0 |

---

## 制限事項 (MVP)

- locale は `ja` のみ
- conditional template の condition 式は単純 boolean のみ (AND/OR 不可)
- 3-way auto merge なし (手動マージ前提)
- archetype 切替の自動 migration なし (`harness-migrator` は将来)
- profile.json schema は v1.0 固定 (migration tool は将来)

---

## 参考資料

- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Sakasegawa — Harness Engineering 2026](https://nyosegawa.com/en/posts/harness-engineering-best-practices-2026/)
- [Claude Code public docs](https://docs.claude.com/en/docs/claude-code)
- 本リポジトリの `assets/knowledge/anthropic-official.md` / `community-patterns.md` (distilled)
