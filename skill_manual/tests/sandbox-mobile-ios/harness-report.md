# Harness Validation Report

- Target: `/home/sophy/projectx/skill_manual/tests/sandbox-mobile-ios`
- Generated: 2026-04-24T16:06:05Z
- Profile: archetype=mobile-app (schema v1.0)
- Validator: v0.1.0

**Summary**: 0 errors, 1 warnings, 0 info

## WARNINGS

### [C13] profile.safety.handles_secrets=true なのに block-secret-commit hook が 未登録 (settings.json で参照されていない)
- **File**: `/home/sophy/projectx/skill_manual/tests/sandbox-mobile-ios`
- **WHY**: 秘密情報を扱う宣言がある harness に秘密漏洩ガードが無い = リスク
- **FIX**: '/harness-generator --force-overwrite .claude/hooks/block-secret-commit.sh' で再生成、または手動配置 + settings.json 登録

