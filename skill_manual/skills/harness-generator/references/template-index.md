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

## production-saas (計画中)

status: planned (Phase 8)

`extends: daily-utility` — daily-utility の templates をベースに以下を追加:

- `production-saas/subagents/code-reviewer.md.tmpl`
- `production-saas/subagents/security-reviewer.md.tmpl`
- `production-saas/subagents/test-author.md.tmpl`
- `production-saas/hooks/pre-pr-gate.sh.tmpl`
- `production-saas/validation/ci.yml.tmpl` (conditional: !ci_external)

## ml-data (計画中)

status: planned (Phase 8)

`extends: daily-utility`:

- `ml-data/subagents/notebook-reviewer.md.tmpl`
- `ml-data/subagents/data-validator.md.tmpl`
- `ml-data/hooks/block-large-artifact.sh.tmpl`
- `ml-data/.gitattributes.tmpl`

## design-heavy (計画中)

status: planned (Phase 8)

`extends: daily-utility`:

- `design-heavy/subagents/ui-reviewer.md.tmpl`
- `design-heavy/subagents/a11y-reviewer.md.tmpl`
- `design-heavy/hooks/post-edit-screenshot.sh.tmpl` (no-op fallback)

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
