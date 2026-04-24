# Check Catalog

harness-validator が実行する全チェック定義。各チェックは一意の ID (C01-C99) と severity を持つ。

## MVP 実装チェック

### C01: CLAUDE.md 行数

- **対象**: `CLAUDE.md`
- **severity**: WARNING
- **閾値**: 50 行以下 (設定可能)
- **WHY**: "Bloated CLAUDE.md files cause Claude to ignore your actual instructions" (Anthropic 公式). 50 行は Sakasegawa の最厳値採用
- **FIX**: 長いセクションを `docs/*.md` に移して `@docs/...md` でインポート
- **DOC_REF**: https://code.claude.com/docs/en/best-practices

### C02: CLAUDE.md トークン数 (概算)

- **対象**: `CLAUDE.md`
- **severity**: WARNING
- **閾値**: 2000 tokens (概算: char / 4)
- **WHY**: primacy bias の悪化閾値 (IFScale 研究)
- **FIX**: C01 と同じ、散文を削る

### C03: 長い単一散文ブロック

- **対象**: `CLAUDE.md`
- **severity**: INFO
- **閾値**: 20 行超の連続非リスト行を 1 ブロックと判定
- **WHY**: ポインタ主義から外れている兆候
- **FIX**: 該当ブロックを別ファイルに切り出し

### C04: settings.json の hook ファイル実在

- **対象**: `.claude/settings.json` の `hooks.*.[].hooks.[].command` パス
- **severity**: ERROR
- **WHY**: 参照先が無ければ hook 発火時にエラー、Claude Code 動作不良
- **FIX**: 該当 script を実装するか、settings.json から entry を削除

### C05: hook matcher の重複

- **対象**: `.claude/settings.json` の `hooks.<event>.[]`
- **severity**: WARNING
- **判定**: 同一 matcher に複数 entry がある場合 (意図的な統合は別)
- **WHY**: 同 matcher の重複は意図しない hook チェインの原因。順序の保証もない
- **FIX**: entries を 1 つに統合し、`hooks` list 内で複数 handler を並べる

### C07: subagent の tools allowlist が既知ツールのみ

- **対象**: `.claude/subagents/*.md` の `tools:` フィールド
- **severity**: ERROR
- **既知ツール**: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch, TodoWrite, TaskCreate, NotebookEdit, Agent, MCP ツール (`mcp__...`)
- **WHY**: 未知ツール名は silently ignored。タイポだと subagent が想定通りに動かない
- **FIX**: 既知のツール名に修正

### C08: CLAUDE.md 参照の subagent が実在

- **対象**: `CLAUDE.md` 本文中の `.claude/subagents/NAME.md` 参照と、`@NAME` メンション
- **severity**: ERROR
- **判定**: 参照先ファイルが存在しない
- **WHY**: ユーザーが呼び出したときにエラー、混乱の原因
- **FIX**: subagent ファイルを配置するか、CLAUDE.md の参照を削除

### C10: secrets の regex 漏れ

- **対象**: `.claude/settings.json`, `.claude/hooks/*.sh`, `.claude/subagents/*.md`
- **severity**: ERROR
- **検知パターン**: AKIA[0-9A-Z]{16}, sk-[A-Za-z0-9]{32+}, ghp_..., xox[baprs]-..., -----BEGIN...PRIVATE KEY-----, `(?i)(api[_-]?key|password|token)[[:space:]]*[:=][[:space:]]*"[^"]{8,}`
- **WHY**: 秘密情報を .claude/ に入れると commit で漏洩
- **FIX**: 環境変数か Secret Manager に移し、スクリプトは `$MY_TOKEN` 参照

### C12: settings.json が有効 JSON + schema 準拠

- **対象**: `.claude/settings.json`
- **severity**: ERROR
- **判定**: JSON パース失敗、または Claude Code settings schema (公式 JSON Schema) に違反
- **WHY**: JSON エラーは Claude Code 起動時に警告、無視されて動かない
- **FIX**: `python3 -m json.tool .claude/settings.json` でエラー箇所確認

### C13: handles_secrets=true なら block-secret-commit hook 必須

- **対象**: `./profile.json` (あれば) + `.claude/hooks/`
- **severity**: WARNING
- **判定**: profile.safety.handles_secrets=true なのに block-secret-commit hook が `.claude/hooks/` に無い、または settings.json で登録されていない
- **WHY**: 秘密情報を扱うと profile で宣言しているのにガードが無い = 危険
- **FIX**: `/harness-generator --force-overwrite` で再 scaffold する

---

## 後回し (MVP 外、Phase 7+)

### C06: permissions の write 許可に対応する guard hook

- **severity**: WARNING
- **判定**: `permissions.allow` に write 系 (`Write(...)`, `Edit(...)`, `Bash(rm:*)`) が含まれるが、対応する PreToolUse hook が無い
- **理由**: write を許すなら安全ネットが必要

### C09: quality_gates.required_checks に対応する hook/CI

- **severity**: WARNING
- **判定**: profile の required_checks に含まれる項目のうち、hook でも CI YAML でも実行されないものを検出
- **理由**: 宣言したチェックが実行されないと ghost gate

### C11: hook shell script が shellcheck を通る

- **severity**: INFO
- **判定**: `shellcheck` コマンドが利用可能なら `.claude/hooks/*.sh` に実行

---

## Severity 判定指針

| severity | 使用基準 |
|---|---|
| **ERROR** | 間違いなく壊れている状態。commit 禁止レベル |
| **WARNING** | 公式/コミュニティのベストプラクティス違反。修正推奨 |
| **INFO** | 改善のヒント。無視しても動く |

詳細は [severity-policy.md](severity-policy.md) を参照。
