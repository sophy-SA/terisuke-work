# テスト

harness-forge の検証戦略。

## E2E テスト

`tests/e2e.sh` が end-to-end の動作確認を行う:

1. **Clean scaffold** — fixture profile から daily-utility harness を scaffold
2. **Idempotent re-run** — 2回目実行で no-op を確認
3. **Validator green** — scaffold 直後の harness で errors==0
4. **破壊テスト (C01)** — CLAUDE.md を 200 行に水増しして C01 WARN が fire
5. **Conditional hooks** — handles_secrets=true fixture で block-secret-commit + block-rm-rf 生成

### 実行方法

```bash
bash tests/e2e.sh
```

依存: `python3`. `jsonschema` / `PyYAML` はあると望ましいが、無くても最低限のチェックは動く。

### サンドボックス

`tests/sandbox/` と `tests/sandbox-secrets/` に scaffold 結果が残る。再実行時に自動で `rm -rf` される。

## Fixtures

`tests/fixtures/` に以下の fixture profile が配置:

| ファイル | 用途 |
|---|---|
| `profile.daily-utility.json` | 標準的な daily-utility プロジェクト |
| `profile.daily-utility-with-secrets.json` | conditional hook 確認用 (handles_secrets, destructive_ops) |
| `answers.daily-utility.yaml` | harness-profiler --batch 用の回答ファイル |

## 後期フェーズで追加予定

- `tests/fixtures/existing-project/` — merge mode (Phase 7) 用
- `tests/fixtures/broken-harness/` — Validator の各チェック fire 確認用
- `tests/test_profile_schema.py` — schema 単体テスト
- `tests/test_generator_daily_utility.py` — template render の単体テスト
- `tests/test_generator_merge.py` — JSON-deep merge の単体テスト
- `tests/test_validator_checks.py` — 各 check_*.py の単体テスト

## 検証不能事項 (手動確認)

- Claude Code に実際にインストールして `/harness-profiler` が起動するか
- SKILL.md の frontmatter を Claude Code がパースできるか
- 実環境で `.claude/hooks/post-edit-format.sh` が PostToolUse で発火するか

これらは MVP 完成後、実環境統合テストで確認する。
