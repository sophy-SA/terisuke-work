# Anthropic 公式: ハーネスエンジニアリング知識ベース

> **用途**: harness-generator が CLAUDE.md / skill / subagent / hook テンプレートを生成する際の**根拠出典**として参照する。各原則には引用元 URL を付す。
> **最終更新**: 2026-04-24 (Phase 0 ディープリサーチ時点)
> **出典言語**: 英語の原典を日本語で distill。原文引用は `> "..."` で保持。

---

## 1. Effective harnesses for long-running agents（ノーススター記事）

**URL**: <https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>
**発行日**: 2025-11-26
**著者**: Justin Young (Anthropic)

### 1.1 核となる主張

> "even a frontier coding model like Opus 4.5 running on the Claude Agent SDK in a loop across multiple context windows will fall short of building a production-quality web app"

最先端モデルでも**適切な harness 設計なしでは本番品質に届かない**。harness エンジニアリングはモデル選択より高レバレッジ。

### 1.2 採用する5原則（claude.ai クローン構築で検証済み）

| #      | 原則                                                               | 実装への示唆                                              |
| ------ | ---------------------------------------------------------------- | --------------------------------------------------- |
| **P1** | **Feature List 方式**: 初期プロンプトを200+機能の明示的リストに展開                    | production-saas テンプレートで `docs/features.md` scaffold |
| **P2** | **Incremental progress**: 一度に1機能のみ実装                             | 全 archetype で「一つずつ」を CLAUDE.md に明記                  |
| **P3** | **Git commit + progress file**: 作業状態を記述的メッセージで記録                 | daily-utility から含める。`docs/progress.md` 雛形           |
| **P4** | **明示的検証指示**: "run tests", "compare screenshots" を workflow に組み込む | Validator C09 (quality_gates → hook/CI 対応) の根拠      |
| **P5** | **init.sh**: 毎セッション開始時の環境確認スクリプト                                 | production-saas 以上で必須、daily-utility は任意             |

### 1.3 セッション開始ルーチン（全 archetype 共通）

> "Run pwd to see the directory you're working in... Read the git logs and progress files to get up to speed... choose the highest-priority feature"

**順序が固定化されるべき:**

1. `pwd` で cwd 確認
2. git log / progress file を読む
3. 既存バグを先に修正
4. **その後**、新機能実装

→ harness-generator の CLAUDE.md.tmpl に「起動時チェックリスト」として埋め込む。

### 1.4 subagents / 多エージェント構成について

> "it's still unclear whether a single, general-purpose coding agent performs best across contexts, or if better performance can be achieved through a multi-agent architecture"
> 
> "specialized agents like a testing agent, a quality assurance agent, or a code cleanup agent, could do an even better job at sub-tasks"

**現時点の Anthropic 公式スタンス**: マルチエージェント構成の優位性は**未検証**だが、特化型エージェント（testing / QA / cleanup）は有望視。
→ MVP は単一 reviewer subagent とし、archetype が上がるにつれ特化型を追加する方針と整合。

---

## 2. CLAUDE.md の設計原則

**URL**: <https://code.claude.com/docs/en/best-practices> (Claude Code Best Practices, 2026 時点)

### 2.1 最重要の指導原理

> "If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost."
> 
> "Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"

**CLAUDE.md が長いと半分は無視される**。harness-validator C01/C02/C03 の存在理由。

### 2.2 Include / Exclude リスト（公式版）

| ✅ Include                | ❌ Exclude                 |
| ------------------------ | ------------------------- |
| Claude が推測できない Bash コマンド | コードを読めば分かること              |
| デフォルトと異なるコードスタイル         | 標準の言語慣習                   |
| テスト実行手順・推奨テストランナー        | 詳細な API ドキュメント（リンクで参照）    |
| リポジトリのルール（ブランチ命名・PR 規約）  | 頻繁に変わる情報                  |
| プロジェクト固有のアーキテクチャ判断       | 長い解説やチュートリアル              |
| 開発環境の癖（必須環境変数）           | ファイルごとの説明                 |
| よくある落とし穴・非自明な振る舞い        | 「clean code を書け」のような自明な助言 |

### 2.3 閾値のルール

**公式には行数上限の数字はない**（best-practices.md はサイズを明示せず「concise」と繰り返すのみ）。ただし skills 公式では `SKILL.md ≤ 500 lines` と明言されている。

harness-forge の採用基準:

- **WARN 閾値 50 行**（プロジェクト固有の現実解）
- **WARN 閾値 2000 tokens**（概算）
- **INFO 閾値: 20行超の単一散文ブロック**（ポインタ主義から外れている兆候）

### 2.4 判定テスト（各行について）

> "For each line, ask: 'Would removing this cause Claude to make mistakes?' If not, cut it."

harness-generator が生成する CLAUDE.md は、この判定を通過した最小セットとする。

### 2.5 インポート構文

> "CLAUDE.md files can import additional files using `@path/to/import` syntax"

```markdown
See @README.md for project overview and @package.json for available npm commands.
```

配置場所:

- `~/.claude/CLAUDE.md` — 全セッション
- `./CLAUDE.md` — プロジェクト共有（commit）
- `./CLAUDE.local.md` — 個人用（gitignore）
- 親ディレクトリ・子ディレクトリ — monorepo 対応

### 2.6 常套アンチパターン

> "The over-specified CLAUDE.md. If your CLAUDE.md is too long, Claude ignores half of it because important rules get lost in the noise. Fix: Ruthlessly prune. If Claude already does something correctly without the instruction, delete it or convert it to a hook."

**CLAUDE.md → Hook への転写パターン**: ルールが守られない場合、prompt ではなく hook で強制する。これは harness-forge の**中核思想**。

---

## 3. Skills の仕様

**URL**:

- <https://code.claude.com/docs/en/skills>
- <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>

### 3.1 SKILL.md フロントマター必須項目

| Field                      | 必須             | 制約                                                                        |
| -------------------------- | -------------- | ------------------------------------------------------------------------- |
| `name`                     | 任意（省略時ディレクトリ名） | lowercase + 数字 + ハイフン、最大 64 文字、予約語禁止 (`anthropic`, `claude`)              |
| `description`              | 推奨             | 最大 1024 文字 (API) / 1536 文字 (`description` + `when_to_use` 合計、Claude Code) |
| `when_to_use`              | 任意             | `description` に追記される。合計で 1536 文字制限                                        |
| `allowed-tools`            | 任意             | スペース区切り or YAML リスト                                                       |
| `disable-model-invocation` | 任意             | `true` で自動呼び出し無効化                                                         |
| `user-invocable`           | 任意             | `false` で `/` メニューから非表示                                                   |
| `context`                  | 任意             | `fork` で subagent 実行                                                      |
| `agent`                    | 任意             | `context: fork` 時に `Explore` / `Plan` / `general-purpose` を指定             |
| `hooks`                    | 任意             | skill-scoped hooks                                                        |
| `paths`                    | 任意             | glob パターンで auto-activation 範囲限定                                           |
| `arguments`                | 任意             | `$name` 置換用の名前付き引数                                                        |
| `model`                    | 任意             | skill 実行中のモデル override                                                    |
| `effort`                   | 任意             | `low` / `medium` / `high` / `xhigh` / `max`                               |

### 3.2 description の書き方（最重要）

> "Always write in third person. The description is injected into the system prompt, and inconsistent point-of-view can cause discovery problems."

**Good**: "Processes Excel files and generates reports"
**Bad**: "I can help you process Excel files" / "You can use this to process Excel files"

**description 式**: `[What the skill does] + [When to use it]` + **具体的トリガー語句** + **negative trigger**

例:

```yaml
description: Extract text and tables from PDF files, fill forms, merge documents.
  Use when working with PDF files or when the user mentions PDFs, forms, or
  document extraction. Do NOT use for general data analysis (use pandas skill
  instead) or for Word/Excel files.
```

### 3.3 命名規則

**Gerund form（現在分詞形）推奨**:

- `processing-pdfs`, `analyzing-spreadsheets`, `managing-databases`

**許容される代替**:

- 名詞句: `pdf-processing`, `spreadsheet-analysis`
- 動詞主導: `process-pdfs`

**避けるべき**:

- 曖昧: `helper`, `utils`, `tools`
- 汎用すぎ: `documents`, `data`, `files`
- 予約語: `anthropic-helper`, `claude-tools`

### 3.4 Progressive Disclosure（3パターン）

**Pattern 1: 高レベルガイド + リファレンス**

```
skill/
├── SKILL.md        # 概要、各 reference への導線
├── REFERENCE.md    # 必要時のみ読み込まれる
└── EXAMPLES.md     # 必要時のみ読み込まれる
```

**Pattern 2: ドメイン別分割**

```
skill/
├── SKILL.md                  # 概要 + ドメインへの導線
└── reference/
    ├── finance.md
    ├── sales.md
    ├── product.md
    └── marketing.md
```

**Pattern 3: 条件付き詳細**

```markdown
For simple edits, modify XML directly.
**For tracked changes**: See [REDLINING.md](REDLINING.md)
**For OOXML details**: See [OOXML.md](OOXML.md)
```

> "Keep references one level deep from SKILL.md. All reference files should link directly from SKILL.md to ensure Claude reads complete files when needed."

ネストした参照はスキャン（`head -100`）されて部分読み込みになるリスク → **フラット構造**を原則とする。

### 3.5 100 行超の reference には TOC を付ける

```markdown
# API Reference

## Contents
- Authentication and setup
- Core methods
- Advanced features
- Error handling
- Examples
```

Claude が partial read する際に全体像を保つための義務。

### 3.6 配置場所の優先順位

| Location   | Path                               | 優先度          |
| ---------- | ---------------------------------- | ------------ |
| Enterprise | managed settings                   | 1 (最高)       |
| Personal   | `~/.claude/skills/<name>/SKILL.md` | 2            |
| Project    | `.claude/skills/<name>/SKILL.md`   | 3            |
| Plugin     | `<plugin>/skills/<name>/SKILL.md`  | namespace 分離 |

同名の場合は高優先度が勝つ。Plugin skills は `plugin-name:skill-name` namespace。

### 3.7 インライン shell 実行

`` !`command` `` は **Claude が content を見る前**に実行され、出力が placeholder を置換する。

```markdown
## Environment
- Node: !`node --version`
- Git status: !`git status --short`
```

複数行は ` ```! ` fenced block。
無効化: `"disableSkillShellExecution": true` (managed settings で強制可能)。

### 3.8 context: fork で subagent 実行

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---
Research $ARGUMENTS thoroughly...
```

skill content が subagent のプロンプトとなる。`agent` で実行環境（モデル・ツール・権限）を決定。

### 3.9 Skills vs Subagents vs Hooks の使い分け

| 目的                          | 手段             |
| --------------------------- | -------------- |
| 再利用可能な playbook / checklist | **Skill**      |
| コンテキストを分離した調査や並列処理          | **Subagent**   |
| **必ず** 実行されるべきアクション         | **Hook**       |
| 外部ツール連携                     | **MCP server** |

> "Hooks are deterministic and guarantee the action happens."
> "CLAUDE.md instructions are advisory."

CLAUDE.md / prompt はアドバイザリー、Hook は決定論的。

### 3.10 Skill 作成ベストプラクティス

1. **Concise is key**: Claude はすでに賢い。tautological な説明は削る
2. **Degrees of freedom**: 壊れやすい処理は low freedom（具体スクリプト）、探索的処理は high freedom（テキスト指示）
3. **全モデルでテスト**: Haiku/Sonnet/Opus
4. **Evaluation-first**: 実問題を解いているか、3シナリオ以上で検証
5. **Solve don't punt**: スクリプトはエラー処理を自前で持つ
6. **No voodoo constants**: 全定数に理由のコメント

---

## 4. Subagents の仕様

**URL**: <https://code.claude.com/docs/en/sub-agents>

### 4.1 何のためにあるか

> "Subagents are specialized AI assistants that handle specific types of tasks. Use one when a side task would flood your main conversation with search results, logs, or file contents you won't reference again."

- **Preserve context** (詳細ログを main から追い出す)
- **Enforce constraints** (ツール制限)
- **Reuse configurations** (user-level で横展開)
- **Specialize behavior** (特化 system prompt)
- **Control costs** (Haiku ルーティング)

### 4.2 ビルトイン subagents

| Agent               | Model | Tools     | 用途                 |
| ------------------- | ----- | --------- | ------------------ |
| **Explore**         | Haiku | Read-only | ファイル探索・コード検索       |
| **Plan**            | 継承    | Read-only | plan mode でのリサーチ   |
| **general-purpose** | 継承    | 全ツール      | 探索 + 修正が両方必要な複雑タスク |

### 4.3 配置場所の優先順位

| Location            | Scope        | Priority |
| ------------------- | ------------ | -------- |
| Managed settings    | Organization | 1 (最高)   |
| `--agents` CLI flag | Session      | 2        |
| `.claude/agents/`   | Project      | 3        |
| `~/.claude/agents/` | User         | 4        |
| Plugin `agents/`    | Plugin       | 5 (最低)   |

### 4.4 frontmatter 必須・任意フィールド

| Field             | 必須  | 説明                                                                            |
| ----------------- | --- | ----------------------------------------------------------------------------- |
| `name`            | ✅   | lowercase + ハイフン                                                              |
| `description`     | ✅   | delegation 判断に使用                                                              |
| `tools`           |     | 許可ツール allowlist。省略時は main から継承                                                |
| `disallowedTools` |     | denylist                                                                      |
| `model`           |     | `sonnet` / `opus` / `haiku` / full ID / `inherit`                             |
| `permissionMode`  |     | `default` / `acceptEdits` / `auto` / `dontAsk` / `bypassPermissions` / `plan` |
| `maxTurns`        |     | agentic turn 上限                                                               |
| `skills`          |     | 起動時 preload する skill 名（full content injected）                                 |
| `mcpServers`      |     | 専用 MCP server                                                                 |
| `hooks`           |     | subagent ライフサイクル hook                                                         |
| `memory`          |     | `user` / `project` / `local` で persistent memory                              |
| `background`      |     | true で常に background 実行                                                        |
| `effort`          |     | `low` ... `max`                                                               |
| `isolation`       |     | `worktree` で独立 git worktree                                                   |
| `color`           |     | UI 識別用                                                                        |
| `initialPrompt`   |     | main session mode でのみ使用                                                       |

### 4.5 Skills preload の挙動

```yaml
---
name: api-developer
skills:
  - api-conventions
  - error-handling-patterns
---
```

> "The full content of each skill is injected into the subagent's context, not just made available for invocation."

Subagent は**親の skill を継承しない** — 明示的に列挙必須。`disable-model-invocation: true` の skill は preload 不可。

### 4.6 persistent memory

```yaml
---
name: code-reviewer
memory: project    # or user / local
---
```

`MEMORY.md` の最初 200 行 (25KB) が system prompt に含まれる。Read/Write/Edit ツールが自動有効化。**project スコープが推奨デフォルト**。

### 4.7 subagent は subagent を spawn できない

> "Subagents cannot spawn other subagents. If your workflow requires nested delegation, use Skills or chain subagents from the main conversation."

ネスト委譲が必要な場合は skill を使う。

### 4.8 description の delegation トリガー

> "To encourage proactive delegation, include phrases like 'use proactively' in your subagent's description field."

例:

```yaml
description: Expert code review specialist. Proactively reviews code for quality,
  security, and maintainability. Use immediately after writing or modifying code.
```

### 4.9 tool allowlist 例

**allowlist**:

```yaml
tools: Read, Grep, Glob, Bash
```

**denylist**（main から継承 − 除外）:

```yaml
disallowedTools: Write, Edit
```

両方指定時は `disallowedTools` を先に適用して残ったプールから `tools` を resolve。

### 4.10 Agent 制限

main thread で `claude --agent` 起動した agent が別 subagent を spawn する場合:

```yaml
tools: Agent(worker, researcher), Read, Bash
```

allowlist のみ許可。`Agent` 単独で全許可、`Agent` 省略で spawn 禁止。

### 4.11 Plugin subagent のセキュリティ制約

> "For security reasons, plugin subagents do not support the `hooks`, `mcpServers`, or `permissionMode` frontmatter fields."

Plugin 配布時はこの3フィールドが無視される。→ `.claude/agents/` か `~/.claude/agents/` で配布する選択肢あり。

---

## 5. Hooks の仕様

**URL**: <https://code.claude.com/docs/hooks-reference>

### 5.1 サポートされるライフサイクルイベント

| イベント                         | タイミング              | matcher 対応                                 |
| ---------------------------- | ------------------ | ------------------------------------------ |
| `SessionStart`               | セッション開始/再開時        | `startup` / `resume` / `clear` / `compact` |
| `UserPromptSubmit`           | プロンプト送信時（処理前）      | なし（常発火）                                    |
| `UserPromptExpansion`        | スラッシュコマンド展開時       | ?                                          |
| `PreToolUse`                 | ツール実行前（**ブロック可能**） | tool name                                  |
| `PermissionRequest`          | パーミッションダイアログ表示時    | ?                                          |
| `PostToolUse`                | ツール実行後（成功）         | tool name                                  |
| `PostToolUseFailure`         | ツール実行失敗時           | tool name                                  |
| `PostToolBatch`              | 並列ツール完了後           | なし                                         |
| `Stop`                       | Claude 応答完了時       | なし                                         |
| `SubagentStart`              | subagent 開始時       | agent type                                 |
| `SubagentStop`               | subagent 完了時       | agent type                                 |
| `StopFailure`                | API エラー終了時         | ?                                          |
| `SessionEnd`                 | セッション終了時           | ?                                          |
| `PreCompact` / `PostCompact` | 圧縮前後               | ?                                          |
| `ConfigChange`               | 設定ファイル変更時          | ?                                          |
| `CwdChanged`                 | cd 実行時             | ?                                          |
| `FileChanged`                | ウォッチ対象ファイル変更時      | ファイル名パターン                                  |

### 5.2 matcher パターン

```json
{
  "matcher": "Bash",              // 完全一致
  "matcher": "Edit|Write",        // OR (| 区切り)
  "matcher": "^Notebook",         // regex
  "matcher": "mcp__memory__.*",   // MCP ワイルドカード
  "matcher": "*"                  // 全マッチ
}
```

### 5.3 hook script の契約

**stdin (JSON)**:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/dir",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "npm test" },
  "tool_use_id": "toolu_01ABC..."
}
```

**stdout (JSON)**:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask|defer",
    "permissionDecisionReason": "理由"
  },
  "additionalContext": "Claude への追加コンテキスト"
}
```

**exit code**:
| Code | 意味 |
|---|---|
| 0 | 成功 (stdout JSON でパース) |
| **2** | **ブロッキングエラー**。stderr が Claude に伝わる |
| その他 | 非ブロッキング、stderr はログへ |

⚠️ **Unix 慣例と異なり、exit 1 は非ブロッキング扱い**。ポリシー強制には必ず `exit 2`。

### 5.4 settings.json 登録構造

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check.sh",
            "timeout": 30,
            "if": "Bash(rm *)"
          }
        ]
      }
    ]
  }
}
```

### 5.5 hook type

| type       | 用途                |
| ---------- | ----------------- |
| `command`  | シェルスクリプト（最も一般的）   |
| `http`     | HTTP POST エンドポイント |
| `mcp_tool` | MCP サーバーのツール呼び出し  |
| `prompt`   | LLM による評価         |
| `agent`    | subagent 起動       |

### 5.6 環境変数

- `$CLAUDE_PROJECT_DIR` — プロジェクトルート
- `${CLAUDE_PLUGIN_ROOT}` — プラグインインストール先
- `${CLAUDE_PLUGIN_DATA}` — プラグイン永続データ

### 5.7 Hook スコープ

| 場所                            | スコープ              |
| ----------------------------- | ----------------- |
| `~/.claude/settings.json`     | 全プロジェクト           |
| `.claude/settings.json`       | プロジェクト（commit）    |
| `.claude/settings.local.json` | プロジェクト（gitignore） |
| Managed Policy                | 組織（管理者制御）         |
| Plugin `hooks/hooks.json`     | プラグイン             |
| Skill/Agent frontmatter       | コンポーネント稼働中のみ      |

### 5.8 セキュリティ

> "Handlers run in the current directory with Claude Code's environment."

Hook は Claude と同じ権限で動く。危険:

- 外部ネットワーク hook は信頼できるエンドポイントのみ
- managed 環境では `"allowManagedHooksOnly": true` で user/project/plugin hook を制限可能
- Plugin subagent は hooks/mcpServers/permissionMode が無効化される

### 5.9 Hook アンチパターン（公式警告から抽出）

1. **stdout 汚染**: `echo "info"` と JSON 出力の混在 → JSON パース失敗
2. **exit 2 と JSON 併用**: exit 2 時は JSON が無視される
3. **matcher 非対応イベントに matcher 書く**: 黙って無視される
4. **timeout 未設定**: デフォルト 600 秒、長処理は明示
5. **SessionStart に長処理**: 毎回発火する、idempotent なガードを入れる
6. **`ask` を hook で返しても UI 入力は取得不可**: `defer` を使う

---

## 6. Best Practices（Claude Code BP）から抽出

**URL**: <https://code.claude.com/docs/en/best-practices>

### 6.1 最重要原則

> "Give Claude a way to verify its work. This is the single highest-leverage thing you can do."

検証手段（テスト / スクリーンショット / 期待出力）を与えることが**最高レバレッジ**。

### 6.2 Explore → Plan → Implement → Commit ワークフロー

**Plan Mode を使う判断基準:**

- 変更が複数ファイルに跨る
- コードに馴染みがない
- アプローチが不確実

**Plan Mode を使わない判断基準:**

- 差分を1文で説明できる（typo 修正 / log 追加 / rename）

### 6.3 Context 管理

> "Claude's context window holds your entire conversation, including every message, every file Claude reads, and every command output. However, this can fill up fast."

- `/clear` をタスク間で積極使用
- `/compact <instructions>` で部分圧縮
- `/rewind` (Esc+Esc) でチェックポイント復元
- 調査は subagent に逃がす

### 6.4 失敗パターン（公式警告）

1. **The kitchen sink session**: 無関係タスクで context 汚染 → `/clear`
2. **Correcting over and over**: 2回訂正しても直らなければ `/clear` + より良い prompt
3. **The over-specified CLAUDE.md**: 長すぎると無視される → 刈り込む or hook に転送
4. **The trust-then-verify gap**: 検証手段なしで受け入れ → テスト / スクリーンショット必須
5. **The infinite exploration**: スコープなしの調査 → subagent に逃がす

### 6.5 パーミッション戦略

- **Auto mode** (`--permission-mode auto`): classifier 判定
- **Allowlist**: `/permissions` で許可ツール明示
- **Sandbox**: OS レベルの分離

### 6.6 Parallel sessions

- Desktop app で multi-session
- Claude Code on the web (cloud VM)
- Agent teams (coordinated)
- Writer/Reviewer パターン（fresh context でレビューするとバイアスが減る）

---

## 7. harness-forge への実装的示唆（要約）

| 項目              | Anthropic 公式由来                                | harness-forge で採用                                                         |
| --------------- | --------------------------------------------- | ------------------------------------------------------------------------- |
| CLAUDE.md 長さ    | 「長いと半分無視される」                                  | WARN 50 行 / 2000 tokens (C01/C02)                                         |
| 指示 → Hook 変換    | 「ルールが守られないなら hook 化」                          | Validator C13 (handles_secrets → block-secret-commit hook 必須)             |
| 検証手段            | 「単一最高レバレッジ」                                   | quality_gates.required_checks を profile に、テンプレで hook/CI 生成                |
| セッション開始ルーチン     | `pwd` → git log → init.sh → bug fix → feature | CLAUDE.md.tmpl に埋め込み                                                      |
| 特化 subagent     | 「未検証だが有望」                                     | MVP は reviewer のみ、production-saas で security/test 追加                      |
| description 三人称 | 「視点が揺らぐと discovery 失敗」                        | テンプレの description フィールド全て三人称で書く                                           |
| name Gerund 形   | 公式推奨                                          | `harness-profiler` / `harness-generator` / `harness-validator` は名詞句だがギリ許容 |
| 参照フラット構造        | 「ネスト refs は partial read される」                 | SKILL.md から references/*.md は全て 1 レベル                                     |
| Hook exit 2     | 「ブロックには exit 2 必須」                            | hook テンプレ全てで明示                                                            |
| Subagent ネスト不可  | 公式明記                                          | harness-generator は skill-creator を「呼ばず」ヒントだけ返す                           |

---

## 8. 未解決・要追加調査

- `SessionStart` / `FileChanged` など一部イベントの matcher 完全仕様（公式 reference が `/hooks-reference#matcher-patterns` にあるが一部曖昧）
- Plugin ディストリビューション時の skill/agent/hook パス解決（`HARNESS_FORGE_ASSETS` 相当の env 変数戦略を Phase 9 で再調査）
- Context7 MCP で最新の skills spec を fetch し直すタイミング（`--refresh-knowledge` Phase 外）
