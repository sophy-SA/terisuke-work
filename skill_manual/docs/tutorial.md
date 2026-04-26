# Tutorial: 初めての harness-forge

このチュートリアルは harness-forge を**初めて使う人**向けです。所要時間は約 10〜15 分。
最後まで進めると、自分のプロジェクトに動作する Claude Code ハーネスが scaffold された状態になります。

> **前提知識**: Claude Code を 1 度以上起動したことがあり、`~/.claude/` ディレクトリが存在すること。

---

## 0. インストール (5 分)

```bash
# 任意の場所に clone
git clone https://github.com/sophy-SA/harness-forge ~/harness-forge
cd ~/harness-forge

# 4 skill を ~/.claude/skills/ に symlink
make install
```

成功すると以下のメッセージが出ます:

```
✓ harness-profiler (symlink)
✓ harness-generator (symlink)
✓ harness-validator (symlink)
✓ harness-evolver (symlink)
```

Claude Code を再起動して、`/harness-profiler` などが menu に出れば OK です。

---

## 1. プロジェクトの準備 (1 分)

scaffold したい既存プロジェクトに `cd` します。**まだ harness が無い空のプロジェクトでも構いません**。

```bash
mkdir -p ~/projects/my-cli-tool
cd ~/projects/my-cli-tool
git init
```

> **重要**: harness-forge は `cwd` (現在の作業ディレクトリ) に scaffold します。
> ホームディレクトリや system 領域では絶対に走らせないでください。

---

## 2. プロファイル作成: `/harness-profiler` (3 分)

Claude Code チャットで以下を入力:

```
/harness-profiler
```

profiler が 2-3 分の対話を始めます。**以下のような流れ**になります:

### 実際のチャット例

```
あなた: /harness-profiler

Claude: harness-profiler を開始します。まず現状を確認させてください。
        [pwd]
        /home/you/projects/my-cli-tool

        [git log]
        (no commits yet)

        [既存ファイル]
        - .git/

        既存の profile.json は見つかりませんでした。新規作成します。

        ---
        Q1.1 このプロジェクトは何をするものですか? 1-2 文で教えてください。

あなた: ローカルのファイルを整理する CLI ツール。重複ファイル検出と
       自動分類をしたい。

Claude: ありがとうございます。

        Q1.2 主要言語を選んでください (複数可、最大3):
        [✓] Python  [ ] TypeScript  [ ] Go  [ ] Rust  ...

あなた: Python だけです

Claude: Q1.3 プロジェクトの主構造は何ですか? (上位2つ)
        - CLI / daily utility / shell script
        - Library / package for publishing
        - Web / SaaS backend or frontend
        - Mobile app
        - ML / data analysis
        - Infrastructure as Code

あなた: CLI です

Claude: Q1.4 デザイン品質 (UI/a11y) は主要関心事ですか? [yes/no]

あなた: no

Claude: ---
        S2: Workflow Preferences

        Q2.1 Plan → Work → Review ワークフローを採用しますか?
        (大きな変更を plan mode で設計してから実装するスタイル)

あなた: いいえ、そこまで大規模じゃないので

Claude: Q2.2 pre-commit の厳格度?
        - none (何もしない)
        - lint-only (lint だけ通す)
        - lint-test (lint + 単体テスト)
        - full (lint + test + typecheck + security-scan)

あなた: lint-only でお願いします

[... S3-S6 まで続く ...]

Claude: インタビュー完了。以下のプロファイルを判定しました:

        Archetype: daily-utility (信号スコア 0.72)
        次点: production-saas (0.12), ml-data (0.06)

        profile.json を ./profile.json に書き出しました。

        次のステップ:
          1. profile.json を確認/編集
          2. /harness-generator で scaffold 実行
```

ポイント:
- **わからない選択肢があれば適当に答えて OK**。後で `profile.json` を直接編集できます
- 質問は全部で **6 セクション (S1-S6)、合計 12-15 問**
- インタビュー中に「やめたい」と言えば中断可能

### 成果物

```bash
ls
# profile.json
cat profile.json | head -10
```

---

## 3. ファイル生成: `/harness-generator` (1 分)

```
あなた: /harness-generator
```

```
Claude: ./profile.json を読み込みます。
        archetype: daily-utility

        以下のファイルを生成します:
          + CLAUDE.md
          + .claude/subagents/reviewer.md
          + .claude/hooks/post-edit-format.sh
          + .claude/hooks/pre-commit-lint.sh
          + .claude/settings.json
          + .git/hooks/pre-commit
          + docs/harness.md
          + .harness-forge.state.json

        ✓ harness 生成完了 (archetype: daily-utility)

        次のステップ:
          1. /harness-validator で整合性確認
          2. 不足している linter / formatter をインストール (ruff, black 等)
```

実物を覗いてみましょう:

```bash
cat CLAUDE.md            # 50 行以下のポインタ主体
cat .claude/subagents/reviewer.md   # レビュアー subagent 定義
cat .claude/hooks/pre-commit-lint.sh  # 自動 lint hook
```

`CLAUDE.md` は **意図的に短く** 作ってあります (Anthropic 公式の "effective harnesses"
方針)。詳細ルールは `.claude/hooks/` で機械的に強制し、CLAUDE.md は要点のみ。

---

## 4. 整合性チェック: `/harness-validator` (1 分)

```
あなた: /harness-validator
```

```
Claude: 静的検査を実行します。

        Harness Validation: 0 errors, 1 warnings, 0 info
          JSON: ./harness-report.json
          MD:   ./harness-report.md

        WARNING:
        - C13: handles_secrets=false なので block-secret-commit hook は不要
               (現状: 配置されていません ✓ 想定通り)

        ✓ errors == 0、merge OK
```

これで scaffold 完了です。

---

## 5. 実際に動かしてみる (3 分)

簡単な Python ファイルを作って commit を試します:

```bash
echo "def hello(): print('hi')" > main.py
git add main.py
git commit -m "feat: hello"
```

**初回 commit 時に `.git/hooks/pre-commit` が発火**して `pre-commit-lint.sh` が走ります。
`ruff` などが install されていれば自動で lint され、エラーがあれば commit が止まります。
無ければ "ruff not found, skipping" のメッセージで通過します。

Claude Code のチャットで何かコードを編集してみると、**PostToolUse hook で自動整形** されます:

```
あなた: main.py に function を追加して

Claude: [Edit main.py: + function bye()]
        # PostToolUse hook が自動実行
        ✓ post-edit-format.sh: black main.py (skipped, not installed)
```

---

## 6. 次のステップ

- **profile.json を編集して再生成**してみる: `intents` を増やしたり `precommit_strictness` を変えたり
- **`/harness-evolver` を使う**: 後日 archetype が更新されたとき、既存 harness の差分のみ反映
- **他 archetype を試す**: 別プロジェクトで `production-saas` や `ml-data` を選んでみる

---

## トラブルシューティング

| 症状 | 対応 |
|---|---|
| `/harness-profiler` が menu に出ない | `make install` 後 Claude Code を再起動。`ls ~/.claude/skills/harness-*` で symlink 確認 |
| `profile.json validation failed` | `assets/knowledge/schema/profile.schema.json` 参照、必須フィールド (`schema_version`, `project.name` 等) を埋める |
| Validator に C04 ERROR が出る | hook script ファイルが無い。`/harness-generator` を再実行するか、生成された hook を意図的に削除した場合は `.claude/settings.json` から登録も消す |
| 既存プロジェクトで scaffold が既存 CLAUDE.md を上書きしないか不安 | 既存 `CLAUDE.md` は `merge: skip_if_exists` なので保護されます。`settings.json` は **JSON deep-merge** で既存内容を保持 |

詳細は `docs/user-guide.md` を参照。各アーキタイプの実例は `docs/use-cases.md` を参照。
