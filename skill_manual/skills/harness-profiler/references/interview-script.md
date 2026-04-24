# インタビュー質問バンク

harness-profiler が `AskUserQuestion` ツールで提示する質問の完全リスト。

---

## S1: Project Shape (必須)

### Q1.1 プロジェクトの目的 (free-form)

- **格納先**: `project.summary`
- **形式**: AskUserQuestion ではなく free-form prompt
- **例文**: "このプロジェクトは何をするものですか? 1-2文で教えてください。"
- **推定ヒント**: README.md の最初の段落があればプレフィル候補として提示

### Q1.2 主要言語 (複数選択、最大3)

- **格納先**: `project.languages[]`
- **選択肢**:
  - Python
  - TypeScript / JavaScript
  - Go
  - Rust
  - Swift
  - Kotlin
  - Ruby
  - Java
  - C#
  - PHP
  - Shell / Bash
  - その他
- **推定ヒント**: manifest file (package.json, pyproject.toml, Package.swift 等) から自動プレフィル

### Q1.3 プロジェクトの主構造 (上位2つ、multiSelect)

- **格納先**: `project.root_kind[]`
- **選択肢 (max 2)**:
  - CLI / daily utility / shell script → archetype=daily-utility の最大信号
  - Library / package for publishing (npm/PyPI/crates/go module) → archetype=library-package の最大信号
  - Web / SaaS backend or frontend → archetype=production-saas の最大信号
  - Mobile app (iOS / Android / React Native / Flutter) → archetype=mobile-app の最大信号
  - ML / data analysis / notebook → archetype=ml-data の最大信号
  - Infrastructure as Code (Terraform / K8s / Helm / Ansible) → archetype=infra-iac の最大信号
  - Mixed (複数に該当)

### Q1.4 デザイン品質は主要関心事か (design_focus フラグ)

- **格納先**: `project.design_focus`
- **選択肢**: yes / no
- **デフォルト**: Q1.3 に `web` か `mobile` を含み、かつ質問省略モード (`--quick`) なら no
- **影響**:
  - yes → `review.specialized_reviewers` に `ui` / `a11y` を自動追加
  - CLAUDE.md に design review workflow 節を追加
  - root_kind に web / mobile があれば visual-regression hook を推奨

---

## S2: Workflow Preferences

### Q2.1 Plan → Work → Review ワークフローを採用?

- **格納先**: `workflow.plan_work_review`
- **選択肢**: yes / no / unsure
- **デフォルト**:
  - unsure → daily-utility: no, library-package / production-saas / mobile-app / ml-data / infra-iac: yes

### Q2.2 pre-commit の厳格度

- **格納先**: `workflow.precommit_strictness`
- **選択肢**:
  - `none` — hook を入れない
  - `lint-only` — lint のみ (推奨 for daily-utility)
  - `lint-test` — lint + 差分テスト (推奨 for library-package)
  - `full` — lint + type + test + security (推奨 for production-saas / mobile-app)

### Q2.3 長時間実行 agent を使うか

- **格納先**: `workflow.long_running_agents`
- **選択肢**: yes / no
- **影響**: yes なら CLAUDE.md に compaction ヒントを追加

---

## S3: Quality Gates

### Q3.1 PR 前に必須の品質チェック (multiSelect)

- **格納先**: `quality_gates.required_checks[]`
- **選択肢**:
  - lint
  - format
  - typecheck
  - unit-test
  - integration-test
  - security-scan
  - a11y
  - visual-regression
  - api-compat (library-package で推奨)
  - semver-check (library-package で推奨)
  - infra-plan-review (infra-iac で推奨)

### Q3.2 CI は外部に既存か?

- **格納先**: `quality_gates.ci_external`
- **選択肢**: yes (GitHub Actions 等が既にある) / no (YAML を scaffold してほしい)

---

## S4: Review & Collaboration

### Q4.1 AI セカンドオピニオンレビューを入れるか?

- **格納先**: `review.ai_second_opinion`
- **選択肢**: yes / no
- **デフォルト**: daily-utility=no, その他=yes

### Q4.2 専門化レビュアー (自動推奨から選択)

- **格納先**: `review.specialized_reviewers[]`
- **選択肢 (multiSelect, 事前計算)**:
  - `code` (常に)
  - `security` (required_checks に security-scan があれば推奨)
  - `a11y` (required_checks に a11y、または design_focus=true なら推奨)
  - `perf` (opt-in)
  - `ui` (design_focus=true なら推奨)
  - `api-compat` (library-package で推奨)
  - `infra` (infra-iac で推奨)

---

## S5: Secrets & Safety

### Q5.1 リポジトリに秘密情報を含む/参照するか?

- **格納先**: `safety.handles_secrets`
- **選択肢**: yes / no
- **影響**: yes → block-secret-commit hook 追加 (Validator C13 要求)

### Q5.2 ガードしたい破壊的操作 (multiSelect)

- **格納先**: `safety.destructive_ops[]`
- **選択肢**:
  - deploy
  - db-migrate
  - force-push
  - rm-rf
  - drop-table
  - terraform-apply (infra-iac 推奨)
  - helm-upgrade (infra-iac 推奨)
  - k8s-apply (infra-iac 推奨)

---

## S6: Meta (必須)

### Q6.1 scaffold する文字列の言語

- **格納先**: `meta.locale`
- **選択肢**: ja / en
- **MVP 制約**: ja のみサポート。en 選択時は警告して ja に強制。

### Q6.2 既存の `.claude/` ディレクトリがあるか?

- **格納先**: `meta.existing_claude_dir`
- **選択肢**: yes / no
- **推定ヒント**: `ls .claude/ 2>/dev/null` で自動プレフィル
- **影響**: yes → Generator は merge mode で動作

### Q6.3 トップ3の must-have 意図 (free-form, 3つ)

- **格納先**: `meta.intents[]`
- **例文**: "このプロジェクトで Claude に絶対守ってほしい3つの意図を、それぞれ1文で教えてください。"

---

## --batch モード用の answers.yaml フォーマット

```yaml
# answers.yaml — 全質問の回答を YAML で記載し、インタビューをスキップする
S1:
  project_summary: "日常的なファイル整理を自動化する CLI ツール"
  languages: ["python"]
  root_kind: ["cli"]
  design_focus: false
S2:
  plan_work_review: false
  precommit_strictness: "lint-only"
  long_running_agents: false
S3:
  required_checks: ["lint", "format"]
  ci_external: false
S4:
  ai_second_opinion: false
  specialized_reviewers: []
S5:
  handles_secrets: false
  destructive_ops: []
S6:
  project_name: "my-tool"
  locale: "ja"
  existing_claude_dir: false
  intents:
    - "一度に1機能だけ実装する"
    - "commit 前に必ず lint を通す"
    - "ファイル移動前に dry-run で対象を確認"
```

---

## 分岐ロジック

- Q1.3 の回答が `[cli]` のみ かつ `precommit_strictness` = `none`|`lint-only` → S3 / S4 / S5 はデフォルト値でスキップ可 (`--quick` モード)
- Q1.4 = yes → Q4.2 の自動推奨に `ui` と `a11y` を含める
- Q1.3 に `library` → Q4.2 の推奨に `api-compat`、Q3.1 の推奨に `api-compat` / `semver-check` を含める
- Q1.3 に `infra` → Q5.2 の推奨に `terraform-apply` / `helm-upgrade` / `k8s-apply`、Q3.1 に `infra-plan-review` を含める
- Q5.1 = yes → Validator C13 により block-secret-commit hook が必須マーク
- Q6.1 = en AND MVP → 警告後に `ja` に強制
