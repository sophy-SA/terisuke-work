# Template Index

harness-generator が archetype ごとに適用する template 一覧。

## daily-utility (MVP 完全実装)

| src (assets/templates/ 配下) | dest (対象プロジェクト cwd 配下) | mode | merge |
|---|---|---|---|
| `daily-utility/CLAUDE.md.tmpl` | `CLAUDE.md` | - | `skip_if_exists` |
| `daily-utility/subagents/reviewer.md.tmpl` | `.claude/subagents/reviewer.md` | - | `overwrite` |
| `daily-utility/hooks/post-edit-format.sh.tmpl` | `.claude/hooks/post-edit-format.sh` | 0755 | `overwrite` |
| `daily-utility/hooks/pre-commit-lint.sh.tmpl` | `.claude/hooks/pre-commit-lint.sh` | 0755 | `overwrite` |
| `daily-utility/settings.patch.json.tmpl` | `.claude/settings.json` | - | `json-deep` |
| `daily-utility/validation/precommit.sh.tmpl` | `.git/hooks/pre-commit` | 0755 | `skip_if_exists` |
| `daily-utility/docs/harness.md.tmpl` | `docs/harness.md` | - | `skip_if_exists` |

### conditional

| condition | src | dest | mode |
|---|---|---|---|
| `HANDLES_SECRETS` | `_shared/hooks/block-secret-commit.sh.tmpl` | `.claude/hooks/block-secret-commit.sh` | 0755 |
| `DESTRUCTIVE_OPS_CONTAINS_RM_RF` | `_shared/hooks/block-rm-rf.sh.tmpl` | `.claude/hooks/block-rm-rf.sh` | 0755 |

## library-package (MVP ✅)

status: complete (Phase 8c 実装済み)

`extends: daily-utility` — 以下を追加:

| src | dest | mode | merge |
|---|---|---|---|
| `library-package/CLAUDE.md.tmpl` | `CLAUDE.md` | - | `skip_if_exists` (親を上書き) |
| `library-package/CHANGELOG.md.tmpl` | `CHANGELOG.md` | - | `skip_if_exists` |
| `library-package/subagents/api-compat-reviewer.md.tmpl` | `.claude/subagents/api-compat-reviewer.md` | - | `overwrite` |
| `library-package/hooks/protect-public-api.sh.tmpl` | `.claude/hooks/protect-public-api.sh` | 0755 | `overwrite` |
| `library-package/hooks/check-changelog.sh.tmpl` | `.claude/hooks/check-changelog.sh` | 0755 | `overwrite` |
| `library-package/hooks/gate-version-tag.sh.tmpl` | `.claude/hooks/gate-version-tag.sh` | 0755 | `overwrite` |
| `library-package/settings.patch.json.tmpl` | `.claude/settings.json` | - | `json-deep` |
| `library-package/docs/harness.md.tmpl` | `docs/harness.md` | - | `skip_if_exists` |

### 主要 hook

- **protect-public-api** (PreToolUse Edit|Write): 公開 API ファイル (src/index.ts, __init__.py, lib.rs 等) 編集時に api-compat-reviewer 呼び出し勧告
- **check-changelog** (PreToolUse Bash): `git commit` 時に src/ 変更ありなら CHANGELOG.md staged 必須
- **gate-version-tag** (PreToolUse Bash): `git tag v*` 時に CHANGELOG.md に該当バージョンエントリ必須

## production-saas (MVP ✅)

status: complete (Phase 8e 実装済み)

`extends: daily-utility` — 以下を追加:

| src | dest | mode | merge |
|---|---|---|---|
| `production-saas/CLAUDE.md.tmpl` | `CLAUDE.md` | - | `skip_if_exists` |
| `production-saas/subagents/code-reviewer.md.tmpl` | `.claude/subagents/code-reviewer.md` | - | `overwrite` |
| `production-saas/subagents/security-reviewer.md.tmpl` | `.claude/subagents/security-reviewer.md` | - | `overwrite` |
| `production-saas/subagents/test-author.md.tmpl` | `.claude/subagents/test-author.md` | - | `overwrite` |
| `production-saas/hooks/pre-pr-gate.sh.tmpl` | `.claude/hooks/pre-pr-gate.sh` | 0755 | `overwrite` |
| `production-saas/hooks/protect-linter-config.sh.tmpl` | `.claude/hooks/protect-linter-config.sh` | 0755 | `overwrite` |
| `production-saas/settings.patch.json.tmpl` | `.claude/settings.json` | - | `json-deep` |
| `production-saas/docs/harness.md.tmpl` | `docs/harness.md` | - | `skip_if_exists` |

### conditional

| condition | src | dest |
|---|---|---|
| `CI_EXTERNAL_FALSE` | `production-saas/validation/ci.yml.tmpl` | `.github/workflows/ci.yml` |

### 主要 hook

- **pre-pr-gate**: `gh pr create` 検知 → lint / typecheck / test ローカル実行 → 失敗で block
- **protect-linter-config**: `.eslintrc` / `biome.json` / `tsconfig.json` / `.prettierrc` 等の編集を block (Sakasegawa の linter config 保護)

## mobile-app (MVP ✅)

status: complete (Phase 8b 実装済み)

`extends: daily-utility` — 以下を追加:

| src | dest | mode | merge |
|---|---|---|---|
| `mobile-app/CLAUDE.md.tmpl` | `CLAUDE.md` | - | `skip_if_exists` (親を上書き) |
| `mobile-app/subagents/mobile-reviewer.md.tmpl` | `.claude/subagents/mobile-reviewer.md` | - | `overwrite` |
| `mobile-app/hooks/block-signing-secret.sh.tmpl` | `.claude/hooks/block-signing-secret.sh` | 0755 | `overwrite` |
| `mobile-app/hooks/protect-manifest.sh.tmpl` | `.claude/hooks/protect-manifest.sh` | 0755 | `overwrite` |
| `mobile-app/settings.patch.json.tmpl` | `.claude/settings.json` | - | `json-deep` |
| `mobile-app/docs/harness.md.tmpl` | `docs/harness.md` | - | `skip_if_exists` |

### conditional (platform 別)

| condition | src | dest |
|---|---|---|
| `MOBILE_PLATFORM_IOS` | `mobile-app/hooks/gate-xcodebuild-release.sh.tmpl` | `.claude/hooks/gate-xcodebuild-release.sh` |
| `MOBILE_PLATFORM_ANDROID` | `mobile-app/hooks/gate-gradle-release.sh.tmpl` | `.claude/hooks/gate-gradle-release.sh` |

### profile 拡張

mobile-app archetype 採用時、`project.mobile_platforms[]` (ios / android / react-native / flutter) で対応プラットフォームを指定。空の場合は汎用テンプレートのみ (platform-specific hook は配置されない)。

## ml-data (MVP ✅)

status: complete

`extends: daily-utility` — 以下を追加:

- `ml-data/CLAUDE.md.tmpl` — 再現性 / DVC / nbstripout 案内 (overrides 親の CLAUDE.md)
- `ml-data/subagents/notebook-reviewer.md.tmpl` — ipynb 構造・再現性レビュアー
- `ml-data/subagents/data-validator.md.tmpl` — schema / 欠損率 / target leak 検査
- `ml-data/hooks/block-large-artifact.sh.tmpl` — >50MB の model/dataset を block (DVC/lfs 案内)
- `ml-data/hooks/check-notebook-output.sh.tmpl` — .ipynb の output 残存に警告
- `ml-data/gitattributes.tmpl` — ipynb diff filter + LFS パターン例
- `ml-data/settings.patch.json.tmpl` — jupyter / dvc / mlflow / pytest 等の許可 + hook 登録
- `ml-data/docs/harness.md.tmpl` — ml-data 構成説明

`BLOCK_LARGE_ARTIFACT_MB` 環境変数で 50MB 閾値を上書き可能。

## infra-iac (MVP ✅)

status: complete (Phase 8d 実装済み)

`extends: daily-utility` — 以下を追加:

| src | dest | mode | merge |
|---|---|---|---|
| `infra-iac/CLAUDE.md.tmpl` | `CLAUDE.md` | - | `skip_if_exists` |
| `infra-iac/subagents/infra-reviewer.md.tmpl` | `.claude/subagents/infra-reviewer.md` | - | `overwrite` |
| `infra-iac/hooks/gate-terraform-apply.sh.tmpl` | `.claude/hooks/gate-terraform-apply.sh` | 0755 | `overwrite` |
| `infra-iac/hooks/gate-k8s-apply.sh.tmpl` | `.claude/hooks/gate-k8s-apply.sh` | 0755 | `overwrite` |
| `infra-iac/hooks/gate-helm-upgrade.sh.tmpl` | `.claude/hooks/gate-helm-upgrade.sh` | 0755 | `overwrite` |
| `infra-iac/hooks/protect-state-files.sh.tmpl` | `.claude/hooks/protect-state-files.sh` | 0755 | `overwrite` |
| `infra-iac/settings.patch.json.tmpl` | `.claude/settings.json` | - | `json-deep` |
| `infra-iac/docs/harness.md.tmpl` | `docs/harness.md` | - | `skip_if_exists` |

### 主要 hook

- **gate-terraform-apply**: `terraform apply -auto-approve` / `terraform destroy` を block、対話的 apply は警告
- **gate-k8s-apply**: `kubectl apply/delete/replace/scale/rollout/patch` を block、`--dry-run` / `diff` / `get` は通過
- **gate-helm-upgrade**: `helm install/upgrade/uninstall/rollback` を block、`template` / `diff` / `lint` は通過
- **protect-state-files**: `*.tfstate` / `kubeconfig` 編集を block、`*.tfvars` に警告

## design_focus flag (旧 design-heavy)

`project.design_focus: true` の場合、archetype を問わず以下が追加される (conditional):

- `_shared/subagents/ui-reviewer.md.tmpl`
- `_shared/subagents/a11y-reviewer.md.tmpl`
- `_shared/hooks/post-edit-screenshot.sh.tmpl` (no-op fallback)

---

## テンプレート変数

以下の変数がすべてのテンプレートで利用可能:

| 変数 | 型 | profile からの導出 |
|---|---|---|
| `PROJECT_NAME` | string | `project.name` |
| `PROJECT_SUMMARY` | string | `project.summary` |
| `LANGUAGES_CSV` | string | `','.join(project.languages)` |
| `PRIMARY_LANGUAGE` | string | `project.languages[0]` |
| `ROOT_KIND_CSV` | string | `','.join(project.root_kind)` |
| `ARCHETYPE_PRIMARY` | string | `archetype_primary` |
| `DESIGN_FOCUS` | bool | `project.design_focus` |
| `LOCALE` | string | `meta.locale` |
| `PRECOMMIT_STRICTNESS` | string | `workflow.precommit_strictness` |
| `PLAN_WORK_REVIEW` | bool | `workflow.plan_work_review` |
| `LONG_RUNNING_AGENTS` | bool | `workflow.long_running_agents` |
| `CI_EXTERNAL` | bool | `quality_gates.ci_external` |
| `HANDLES_SECRETS` | bool | `safety.handles_secrets` |
| `AI_SECOND_OPINION` | bool | `review.ai_second_opinion` |
| `REQUIRED_CHECKS_CSV` | string | `','.join(quality_gates.required_checks)` |
| `REQUIRED_LINT` | bool | `'lint' in quality_gates.required_checks` |
| `REQUIRED_TYPECHECK` | bool | `'typecheck' in quality_gates.required_checks` |
| `REQUIRED_UNIT_TEST` | bool | `'unit-test' in quality_gates.required_checks` |
| `REQUIRED_SECURITY_SCAN` | bool | `'security-scan' in quality_gates.required_checks` |
| `REQUIRED_A11Y` | bool | `'a11y' in quality_gates.required_checks` |
| `DESTRUCTIVE_OPS_CONTAINS_RM_RF` | bool | `'rm-rf' in safety.destructive_ops` |
| `DESTRUCTIVE_OPS_CONTAINS_DEPLOY` | bool | `'deploy' in safety.destructive_ops` |
| `DESTRUCTIVE_OPS_CONTAINS_FORCE_PUSH` | bool | `'force-push' in safety.destructive_ops` |
| `INTENT_1` | string | `meta.intents[0]` or `""` |
| `INTENT_2` | string | `meta.intents[1]` or `""` |
| `INTENT_3` | string | `meta.intents[2]` or `""` |
| `GENERATED_AT` | string (ISO) | 現在時刻 |
| `GENERATOR_VERSION` | string | harness-forge バージョン |

## テンプレート構文

- `{{VAR}}` — 変数の値で置換。boolean は `true`/`false` 文字列、配列は CSV 化される
- `{{#if VAR}}...{{/if}}` — VAR が truthy なブロック展開
- `{{#unless VAR}}...{{/unless}}` — VAR が falsy なブロック展開
- `{{#if VAR}}...{{else}}...{{/if}}` — MVP 未サポート (Phase 7+)
- ネスト: サポートしない (MVP)。必要なら別テンプレートに分割

## 変数追加の手順 (将来の拡張)

1. `apply_scaffold.py` の `flatten_profile()` に変数を追加
2. このドキュメントの表に記載
3. `tests/fixtures/profile.daily-utility.json` でレンダリング確認
