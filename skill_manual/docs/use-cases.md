# Use Cases: Archetype 別シナリオ集

このドキュメントは **6 archetype それぞれの典型シナリオ + チャット応答の実例** を集めたものです。
自分のプロジェクトに近いケースを参考に、profile 回答や生成後のワークフローを把握できます。

> **このドキュメントの読み方**: 各セクションは独立しているので、自分のプロジェクトに合うものだけ読んで OK。

---

## 1. daily-utility — 個人 CLI / 日常スクリプト

### こんなプロジェクト向け

- ローカルでファイルを整理する Python スクリプト
- 個人で使う bash util 集
- 週末に作って自分だけが使う npm CLI tool
- 一発作業のデータ変換 script

### profile 回答の典型例

```
Q1.1 (目的): ローカルのファイルを整理する CLI ツール
Q1.2 (言語): Python
Q1.3 (構造): CLI / daily utility
Q1.4 (design_focus): no
Q2.1 (Plan→Work→Review): no
Q2.2 (precommit): lint-only
Q2.3 (long-running agents): no
Q3.1 (required_checks): lint, format
Q3.2 (CI external): no
Q4.1 (AI second opinion): no
Q4.2 (specialized reviewers): (なし)
Q5.1 (handles secrets): no
Q5.2 (destructive ops): (なし)
Q6 (intents): "1機能ずつ実装", "commit 前に lint 通す"
```

### 生成されるもの

- `CLAUDE.md` — 50 行以下、起動時ルーチンと作業ルール
- `.claude/subagents/reviewer.md` — read-only 汎用レビュアー
- `.claude/hooks/post-edit-format.sh` — 言語別 formatter 自動検出 (black / prettier 等)
- `.claude/hooks/pre-commit-lint.sh` — 言語別 linter 自動検出 (ruff / eslint 等)
- `.claude/settings.json` — readonly Bash 許可
- `.git/hooks/pre-commit` — `pre-commit-lint.sh` を呼ぶ wrapper

### 典型的なチャット応答

```
あなた: ファイルを SHA256 でグルーピングする関数を main.py に追加して

Claude: [Edit main.py]
        # PostToolUse: post-edit-format.sh が auto で走る
        ✓ ruff format main.py (modified 1 file)

        次に "@reviewer" を呼んで差分見ますか?

あなた: お願い

Claude: @reviewer agent を起動。

        [reviewer]: 差分を読みました。
          - SHA256 計算でファイル全体を read していますが、巨大ファイル
            (>1GB) で OOM の可能性。chunk 読みに変更を推奨。
          - test ケースが無いので tests/test_main.py を追加推奨。

        どちらか対応しますか?
```

### 注意点

- linter / formatter は **手動 install が前提** (`pip install ruff black`)
- `precommit_strictness=full` にすると test も要求される (個人 util には重いかも)
- handles_secrets を使う場合は `block-secret-commit.sh` が追加される (.env / *.key の commit 阻止)

---

## 2. library-package — 公開ライブラリ

### こんなプロジェクト向け

- npm publish する TypeScript ライブラリ
- PyPI で配布する Python パッケージ
- crates.io の Rust crate
- semver / CHANGELOG / API 後方互換が重要

### profile 回答の典型例

```
Q1.1: HTTP リクエストの retry 戦略を抽象化する npm パッケージ
Q1.2: TypeScript
Q1.3: Library / package for publishing
Q2.1 (Plan→Work→Review): yes (breaking change の判断が重要)
Q2.2: lint-test
Q3.1: lint, format, typecheck, unit-test
Q3.2 (CI): yes (GitHub Actions 既存)
Q5.2: (force-push を含めない、tag 削除厳禁)
intents: "breaking change は major bump", "CHANGELOG 必須"
```

### 生成されるもの (daily-utility 継承)

追加分:
- `.claude/subagents/api-compat-reviewer.md` — public API の変更を追跡
- `.claude/hooks/protect-public-api.sh` — `src/index.ts` 等の編集に警告
- `.claude/hooks/check-changelog.sh` — `src/` 編集時に CHANGELOG が staged 必須
- `.claude/hooks/gate-version-tag.sh` — `git tag vX.Y.Z` 前に CHANGELOG エントリ確認
- `CHANGELOG.md` (Keep a Changelog 形式の雛形)

### 典型的なチャット応答

```
あなた: retry の interval 計算を exponential backoff に変えたい

Claude: src/retry.ts を見ます。
        [Read src/retry.ts]

        この関数は public API (src/index.ts から re-export) です。
        @api-compat-reviewer を先に呼んで影響を確認することを推奨します。

あなた: お願い

Claude: @api-compat-reviewer agent を起動。

        [api-compat-reviewer]: シグネチャ変更が breaking かを判定。
          - retry(fn, options) の options 型は同じ → backwards compatible
          - 内部実装のみ変更 → minor bump (0.x → 0.x+1) で OK
          - test ケース追加を推奨

        実装を進めますか?

あなた: 進めて

Claude: [Edit src/retry.ts]
        ✓ ruff/prettier auto-format 完了

        commit 前に CHANGELOG.md の Unreleased セクションを更新する必要が
        あります (check-changelog.sh hook が要求)。
        以下を提案:

        ## [Unreleased]
        ### Changed
        - retry interval を exponential backoff に変更 (#42)

        この内容で CHANGELOG.md を更新しますか?
```

### 注意点

- `gate-version-tag.sh` は **CHANGELOG にバージョン記載があるか** を grep でチェックするだけ。release 自動化は別途 GitHub Actions で
- `check-changelog.sh` の bypass は `SKIP_CHANGELOG_CHECK=1` (chore commit などで)
- monorepo は MVP 想定外 (root に CHANGELOG.md が無い構成は要 hook 改変)

---

## 3. production-saas — 商用 SaaS

### こんなプロジェクト向け

- Next.js + Supabase + Stripe の SaaS
- 認証・決済・PII を扱う web アプリ
- CI/CD パイプライン稼働中
- チーム開発、コードレビュー必須

### profile 回答の典型例

```
Q1.1: SaaS for X. Stripe + Supabase auth.
Q1.2: TypeScript
Q1.3: Web / SaaS backend or frontend
Q1.4 (design_focus): yes (UI/UX も重要)
Q2.1: yes (大きな変更は plan first)
Q2.2: full (lint + test + typecheck + security-scan)
Q3.1: lint, format, typecheck, unit-test, integration-test, security-scan
Q3.2: yes
Q4.1 (AI second opinion): yes
Q4.2 (specialized reviewers): code, security
Q5.1 (handles secrets): yes
Q5.2: deploy, db-migrate, force-push
intents: "認証決済は security-reviewer 必須", "PR 前に typecheck/test 必須"
```

### 生成されるもの (daily-utility 継承)

- `.claude/subagents/code-reviewer.md` — 厳密版 (パフォーマンス + テスト網羅)
- `.claude/subagents/security-reviewer.md` — OWASP Top 10 観点
- `.claude/subagents/test-author.md` — TDD でテスト追加
- `.claude/hooks/pre-pr-gate.sh` — `gh pr create` 前に typecheck + test 必須
- `.claude/hooks/protect-linter-config.sh` — eslintrc / biome.json 等の編集を block (Sakasegawa 推奨)
- `.claude/hooks/block-secret-commit.sh` — .env 等の commit 阻止
- `.github/workflows/ci.yml` — Lint / Typecheck / Test job

### 典型的なチャット応答

```
あなた: Stripe Webhook の署名検証を追加して

Claude: 認証・決済まわりは @security-reviewer の事前相談を推奨します。
        まず Plan mode で設計しましょうか? (Esc + p)

あなた: そうしよう

[Plan mode で設計後]

Claude: 設計確定。実装します。
        [Edit app/api/stripe/webhook/route.ts]
        ✓ post-edit-format: prettier auto

        実装完了。@security-reviewer に依頼します。

        [security-reviewer]: OWASP A02 (Cryptographic Failures) 観点で確認。
          ✓ stripe.webhooks.constructEvent で署名検証
          ✓ raw body を使用 (parsed body だと verification 失敗)
          ✓ STRIPE_WEBHOOK_SECRET は env 経由
          ⚠ replay attack 防止: timestamp tolerance を 5 分に
          → 修正します

あなた: PR 作成まで進めて

Claude: pre-pr-gate hook が走ります。
        ✓ npm run typecheck
        ✓ npm run test
        ✓ snyk test (security-scan)
        ✓ All checks passed

        gh pr create を実行します。
```

### 注意点

- `pre-pr-gate.sh` の実行時間が長い (フル test だと数分) → 緊急時は `SKIP_PRE_PR_GATE=1`
- `protect-linter-config.sh` は **lint ルール緩和の誘惑を構造的に封じる** ため。一時 bypass: `SKIP_LINTER_CONFIG_PROTECTION=1`
- `ci.yml` は **既存 `.github/workflows/` がある場合 skip_if_exists で保護**
- handles_secrets=true でも `git secrets` は別途設定推奨 (本 hook はあくまで Claude Code 経由の Edit/Write のみ block)

---

## 4. mobile-app — iOS / Android / RN / Flutter

### こんなプロジェクト向け

- iOS Swift アプリ (xcodebuild)
- Android Kotlin (gradle)
- React Native / Flutter のクロスプラットフォーム

### profile 回答の典型例

```
Q1.1: iOS の家計簿アプリ。SwiftUI + SwiftData.
Q1.2: Swift
Q1.3: Mobile app
project.mobile_platforms: ["ios"]
Q2.2: lint-only
Q5.1: yes (signing key)
Q5.2: (unsigned release block)
intents: "署名 secret は絶対 commit しない", "TestFlight release は手動承認"
```

### 生成されるもの

- `.claude/subagents/mobile-reviewer.md` — モバイル特有のレビュー観点
- `.claude/hooks/block-signing-secret.sh` — *.p12 / *.keystore / GoogleService-Info.plist 等の commit を block
- `.claude/hooks/protect-manifest.sh` — Info.plist / AndroidManifest.xml の編集に警告
- (iOS のみ) `.claude/hooks/gate-xcodebuild-release.sh` — Release configuration の archive を block (debug は通過)
- (Android のみ) `.claude/hooks/gate-gradle-release.sh` — `assembleRelease` 等を block

### 典型的なチャット応答

```
あなた: API key を env から読むように変える

Claude: [Edit Sources/Config.swift]
        ✓ post-edit-format auto

あなた: Info.plist に新しい permission を追加して

Claude: ⚠ Info.plist は protect-manifest.sh の警告対象です。
        permission の追加は審査リジェクト要因になりやすいので、
        @mobile-reviewer に確認を推奨します。

        @mobile-reviewer: NSCameraUsageDescription の追加は適切か?
          - 用途: バーコードスキャン → OK
          - 文言: "領収書をスキャンするためにカメラを使用します" → 推奨文言

        進めますか?

あなた: TestFlight に出したい、archive コマンドを実行

Claude: ⚠ gate-xcodebuild-release.sh が "Release archive" を block しました。

        WHY: TestFlight / App Store release は手動承認が必須 (Q5.2 で
             unsigned release block 設定済み)
        FIX:
          1. Xcode GUI から archive (推奨)
          2. または `SKIP_XCODEBUILD_RELEASE_GATE=1` で一時 bypass
          3. CI 経由 (fastlane 等) で実行

        Debug build は通過します:
          xcodebuild -scheme MyApp -configuration Debug build
```

### 注意点

- `mobile_platforms[]` の指定で iOS のみ / Android のみ / RN マルチプラットフォーム を切替
- React Native は両方の hook が配置される
- 署名 secret block は filename pattern マッチ。custom 命名規則がある場合は hook を編集
- iOS シミュレータ build は通常通過、release configuration のみ block

---

## 5. ml-data — ML / Data パイプライン

### こんなプロジェクト向け

- Jupyter Notebook 中心の実験プロジェクト
- pytorch / scikit-learn でモデル学習
- DVC / MLflow でデータ・モデル管理
- 大容量 dataset / model artifact が頻発

### profile 回答の典型例

```
Q1.1: 顧客 churn 予測モデル。pandas + sklearn。
Q1.2: Python
Q1.3: ML / data analysis / notebook
Q2.2: lint-only
Q2.3 (long-running agents): yes (モデル学習が数時間)
Q3.1: lint, format, unit-test
Q5.2: (なし、ただし大容量 artifact ブロック必須)
intents: "random seed 必ず固定", "model は DVC", "notebook output は strip"
```

### 生成されるもの

- `.claude/subagents/notebook-reviewer.md` — ipynb 構造・再現性レビュアー
- `.claude/subagents/data-validator.md` — schema / 欠損率 / target leak 検査
- `.claude/hooks/block-large-artifact.sh` — 50MB 超 (デフォルト) を block (DVC / lfs 案内)
- `.claude/hooks/check-notebook-output.sh` — .ipynb の output 残存に警告
- `.gitattributes` — ipynb diff filter + LFS パターン例

### 典型的なチャット応答

```
あなた: notebooks/eda.ipynb で churn 率の分布を見たい

Claude: [Edit notebooks/eda.ipynb: + cell with df.churn.value_counts()]
        ⚠ check-notebook-output.sh: notebook に output セルが残っています
          commit 前に nbstripout を推奨

        @data-validator で schema 確認しますか?

あなた: お願い

Claude: @data-validator: data/raw/customers.parquet を確認。
          - 列 27 個、行 50,000
          - churn 列: bool / 欠損 0%
          - signup_date: datetime / 欠損 2.3%
          - lifetime_value: float / 欠損 0% / 異常値 (>10^6) 12 件
          ⚠ test/train split が時系列で分かれていません (target leak リスク)
          → group split を推奨

あなた: 学習済みモデル model.pkl を保存

Claude: ⚠ block-large-artifact.sh が 200MB の .pkl を block しました。

        WHY: 50MB 超のファイルを git に commit すると push/clone が劣化
        FIX:
          1. DVC で管理: dvc add model.pkl → .dvc メタのみ commit
          2. git-lfs で管理: git lfs track "*.pkl"
          3. HuggingFace Hub に push
          4. 一時 bypass: BLOCK_LARGE_ARTIFACT_MB=300 (非推奨)

        DVC 推奨。dvc init していますか?
```

### 注意点

- 50MB 閾値は `BLOCK_LARGE_ARTIFACT_MB` で変更可
- notebook output は **警告のみ** (block ではない)。commit 前に手動 nbstripout または `jupyter nbconvert --clear-output --inplace`
- `.gitattributes` の DVC / LFS パターンは **コメントアウト済み**。利用時はコメント解除

---

## 6. infra-iac — Infrastructure as Code

### こんなプロジェクト向け

- Terraform で AWS / GCP リソース管理
- Kubernetes manifests / Helm chart
- Ansible playbook
- 本番環境への apply に審査必須

### profile 回答の典型例

```
Q1.1: AWS 上の Web アプリ infrastructure。Terraform + EKS.
Q1.2: (Terraform / HCL は free-form で記述)
Q1.3: Infrastructure as Code
Q2.2: lint-only (terraform fmt / tflint)
Q5.2: deploy, db-migrate, force-push, terraform-apply
intents: "apply は手動承認", "tfstate は外部 backend", "destroy 厳禁"
```

### 生成されるもの

- `.claude/subagents/infra-reviewer.md` — IaC 観点 (security group / IAM / cost)
- `.claude/hooks/gate-terraform-apply.sh` — `terraform apply -auto-approve` / `destroy` を block (plan は通過)
- `.claude/hooks/gate-k8s-apply.sh` — `kubectl apply` を block (`--dry-run` は通過)
- `.claude/hooks/gate-helm-upgrade.sh` — `helm upgrade` を block (`template` / `diff` は通過)
- `.claude/hooks/protect-state-files.sh` — `*.tfstate` / `terraform.tfvars` の編集を block

### 典型的なチャット応答

```
あなた: 新しい RDS インスタンスを Terraform で追加して

Claude: [Edit terraform/rds.tf]
        ✓ terraform fmt 自動実行

        @infra-reviewer に確認を推奨します。

        [infra-reviewer]:
          ✓ multi_az = true (本番想定で適切)
          ⚠ deletion_protection が未指定 (default false) → true 推奨
          ⚠ backup_retention_period が 1 (短い) → 7+ 推奨
          ⚠ publicly_accessible のチェックが無い → false 明示推奨
          [security] storage_encrypted = true 確認 OK

あなた: terraform plan で確認したい

Claude: terraform plan を実行します。
        ✓ gate-terraform-apply.sh: plan は通過 OK

        Plan: 1 to add, 0 to change, 0 to destroy.
        ...

あなた: じゃあ apply

Claude: ⚠ gate-terraform-apply.sh が `terraform apply -auto-approve` を block しました。

        WHY: 本番リソース変更は手動承認必須 (Q5.2 で terraform-apply 設定)
        FIX:
          1. インタラクティブ apply: `terraform apply` (yes 入力)
          2. CI 経由 (Atlantis / Terraform Cloud)
          3. 一時 bypass: `SKIP_TERRAFORM_APPLY_GATE=1` (推奨しない)

        どうしますか?
```

### 注意点

- `gate-*-apply.sh` は **コマンド文字列の grep**。alias やスクリプト経由は検知できない
- `protect-state-files.sh` は `*.tfstate` / `*.tfstate.backup` / `terraform.tfvars` を default 保護
- multi-cloud / multi-account 環境では IAM の reviewer 強化を推奨

---

## デザイン重視プロジェクト (`design_focus: true`)

archetype 横断で `project.design_focus: true` にすると以下が追加:

- `review.specialized_reviewers` に `ui` / `a11y` を追加 (production-saas のみ activate)
- CLAUDE.md に design review workflow 節 (将来)
- `root_kind` に `web` / `mobile` を含む場合 visual-regression hook を提案 (将来)

> MVP では `design_focus` フラグの読み取りのみ実装。本格的な UI/a11y reviewer は将来。

---

## 複数 archetype を mix したい場合

たとえば「production-saas + ml-data」(SaaS バックエンド + ML inference API):

**MVP では archetype は単一**。以下のいずれかを推奨:

1. **支配的な archetype を選ぶ** + 不足分は手動追加
   - 例: `production-saas` を選び、`ml-data/hooks/block-large-artifact.sh` を手動コピー
2. **monorepo で分離**
   - `apps/web/` で production-saas、`apps/ml/` で ml-data を別々に scaffold
3. **`harness-evolver` で部分反映** (上級者向け)
   - 主 archetype scaffold 後、別 archetype の templates dir を指定して `--apply` で hook のみ追加

将来的には `extends:` 機構を public 化して mix 可能にする予定。

---

## まとめ

| ケース | 推奨 archetype | キー hook |
|---|---|---|
| 個人 CLI / shell util | daily-utility | post-edit-format / pre-commit-lint |
| 公開 npm / PyPI | library-package | check-changelog / gate-version-tag |
| 商用 web SaaS | production-saas | pre-pr-gate / protect-linter-config |
| iOS / Android アプリ | mobile-app | block-signing-secret / gate-release |
| Jupyter ML 実験 | ml-data | block-large-artifact / check-notebook-output |
| Terraform / K8s | infra-iac | gate-*-apply / protect-state-files |

迷ったら **profiler のスコア結果** を信じて OK (上位 archetype に 0.5 以上の差があれば即決)。
スコアが拮抗する場合は本ドキュメントの該当セクションを読み比べて判断してください。
