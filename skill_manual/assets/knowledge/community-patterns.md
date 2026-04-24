# コミュニティ実装パターン知識ベース

> **用途**: harness-generator が archetype 別テンプレートを生成する際の**パターン台帳**。Anthropic 公式（`anthropic-official.md`）を骨格に、実戦投入された実装知を肉付け。
> **最終更新**: 2026-04-24 (Phase 0 ディープリサーチ時点)
> **調査対象**: 5リポジトリ / 記事

---

## 0. 定量エビデンス（harness の効果）

**出典**: [Sakasegawa "Harness Engineering: A Comprehensive Framework" (2026-03)](https://nyosegawa.com/en/posts/harness-engineering-best-practices-2026/)

| メトリクス                               | 影響                                |
| ----------------------------------- | --------------------------------- |
| **同モデルで harness を変更**               | **+22 ポイント** (Morph 研究、SWE-bench) |
| モデル自体を差し替え                          | +1 ポイント                           |
| **= harness 変更は モデル差し替えの ~22 倍の効果** |                                   |
| OpenAI 実験: 週1回の AI コード整理に消費         | 開発時間の **20%** → 機械的ルール強制で削減可能     |

**示唆**: `harness-forge` の価値命題はここに集約される。ユーザーに "harness こそが leverage" と伝える根拠。

---

## 1. 調査対象サマリー

| #   | ソース                                                                                                              | 種別             | 鍵となる概念                                              |
| --- | ---------------------------------------------------------------------------------------------------------------- | -------------- | --------------------------------------------------- |
| A   | [Chachamaru127/claude-code-harness v4](https://github.com/Chachamaru127/claude-code-harness)                     | GitHub repo    | Plan→Work→Review→Release, 13 rule guardrail engine  |
| B   | [Sakasegawa "Harness Engineering 2026"](https://nyosegawa.com/en/posts/harness-engineering-best-practices-2026/) | Blog (2026-03) | Enforce with mechanisms not prompts, speed layers   |
| C   | [HumanLayer "Skill Issue"](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents)    | Blog           | Task-type subagents (role-based fails), context rot |
| D   | [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)              | GitHub repo    | `<important if>` タグ, context 30-40% keep            |
| E   | [revfactory/harness](https://github.com/revfactory/harness)                                                      | GitHub repo    | **harness-forge と類似**: ドメイン記述→チーム生成                 |

---

## 2. 採用するパターン（harness-forge で反映）

### 2.1 **Speed Layer 原則** (B)

> "フィードバック速度が品質を決定する。チェックをなるべく高速層に移行せよ。"

| 層                    | 応答速度 | 例                              |
| -------------------- | ---- | ------------------------------ |
| **PostToolUse Hook** | ミリ秒  | Biome format / Oxlint auto-fix |
| **Pre-commit**       | 秒    | ruff / prettier / mypy         |
| **CI/CD**            | 分    | test suite / integration test  |
| **人間レビュー**           | 時間   | code review                    |

**harness-forge での反映**:

- daily-utility: PostToolUse format hook + pre-commit lint
- production-saas: 全層（PostToolUse → pre-commit → CI → review）
- 検証ルールは **可能な限り高速層** に下ろすのがデフォルト

### 2.2 **Enforce Quality with Mechanisms, Not Prompts** (B)

> "'テストを書いてね' という指示では不十分。必ず機械的強制（Hook / pre-commit）で enforce する。"

**実装パターン**:

- CLAUDE.md に書かずに hook で検知
- hook script のエラー出力に `WHY` と `FIX` を埋め込む（Claude は無視できなくなる）
- Linter 設定ファイル自体を PreToolUse hook で保護（`eslintrc`, `biome.json`, `pyproject.toml`, `tsconfig.json`, `.prettierrc` への書き込みブロック）

**harness-forge での反映**: `handles_secrets=true` プロファイル → block-secret-commit hook 必須（C13 チェック）。同様に `precommit_strictness=full` → pre-commit テスト hook を生成。

### 2.3 **エラーメッセージに FIX を埋め込む** (B)

```
ERROR: [違反内容]
WHY:   [理由 + ADR へのリンク]
FIX:   [修正ステップ + コード例]
```

**harness-forge での反映**: Validator の severity-policy.md にこの3点セット記載を義務化。全 hook スクリプトのテンプレでも `exit 2` 時の stderr に同形式で出力させる。

### 2.4 **Task-type Subagents, NOT Role-based** (C)

> "'フロントエンド担当'・'バックエンド担当' などの役割分けは**機能しない**。代わりに **タスク型** の分離を使え。"

**HumanLayer の根拠**: Chroma の "context rot" 研究でコンテキスト長 → 性能低下が実証。役割ベースだと中間ノイズが蓄積する。

**有効な分離軸**:

- **Research** (Explore / 情報収集)
- **Implement** (コード書き換え)
- **Verify** (テスト / 検証)
- **Review** (視点別コードレビュー)

**harness-forge での反映**:

- MVP (daily-utility) の subagent は `reviewer` のみ（task-type）
- production-saas では `code-reviewer` / `security-reviewer` / `test-author`（各 task-type）
- 「backend-engineer」「frontend-engineer」のような role subagent は**作らない**

### 2.5 **Context-Efficient Back-pressure** (C)

> "検証メカニズム（型チェック・テスト・ビルド）は**成功は無言、失敗のみ浮上**させよ。"

**harness-forge での反映**: 全 hook テンプレで `exit 0` 時は stderr を黙らせる（`>&2 echo` しない）。`exit 2` のみで詳細出力。これで context 汚染を最小化。

### 2.6 **4視点レビュー体系** (A)

Chachamaru127 repo の Reviewer agent が実装している4観点:

1. **Security** (脆弱性・秘密情報漏洩)
2. **Performance** (N+1・アルゴリズム複雑度)
3. **Quality** (可読性・テスト coverage)
4. **Accessibility** (UI archetype で特に)

**harness-forge での反映**:

- MVP (daily-utility): Quality のみの単一 reviewer
- production-saas: Security + Quality + Performance
- design-heavy: Quality + A11y
- ml-data: Quality + Performance (データ妥当性検証)

### 2.7 **Minimum Viable Harness の時間軸** (B)

Sakasegawa 記事の段階的構築プラン:

| 期間       | 導入物                                                                      |
| -------- | ------------------------------------------------------------------------ |
| **週1**   | CLAUDE.md 雛形（ポインタのみ）+ pre-commit hook + PostToolUse auto-format          |
| **週2-4** | エージェント失敗を見てから test/linter ルール追加（**事前最適化禁止**）+ Plan→Execute→Verify ワークフロー |
| **月2-3** | カスタム linter（FIX 指示埋め込み）+ ADR + archgate pattern                          |
| **月3+**  | Plankton パターン（20+ linter 統合）+ garbage-collection agent                   |

**harness-forge での反映**:

- daily-utility = 週1 相当の MVP harness
- production-saas = 週2-4 相当
- 「月2-3」以降はユーザーが自力で増築するフェーズ。harness-forge は scaffold までを責務とする。

### 2.8 **iteration-driven development** (C)

> "出荷を優先。失敗が出たら原因を harness に求め、再発防止設計。事前最適化は避けよ。"

**harness-forge での反映**: profiler で「予想される失敗モード」を全部聞き出そうとしない。`intents` 3つに絞る。過剰設計を防ぐ。

### 2.9 **CLAUDE.md の厳格な上限** (B, C, D)

| ソース          | 推奨値                                                |
| ------------ | -------------------------------------------------- |
| Anthropic 公式 | 行数明示なし、ruthlessly prune                            |
| Sakasegawa   | **50 行以下**（IFScale 研究：150-200 行超で primacy bias 悪化） |
| HumanLayer   | **60 行未満**                                         |
| shanraisshan | **60 行理想、200 行上限**                                 |

**harness-forge での採用**: `C01 WARN @ 50 行` (Sakasegawa 最厳値を採用)。ユーザーが後で緩めたければ設定可能。

### 2.10 **Context Budget Management** (D)

> "Claude Code の context 使用率を ~30-40% に保つこと。`/rewind` で失敗時のコンテキスト汚染を回避。"

**harness-forge での反映**: 直接 scaffold には関わらないが、CLAUDE.md.tmpl の末尾に「`/clear` between tasks, `/rewind` when stuck」を埋め込む。

### 2.11 **設定駆動 > CLAUDE.md 記述** (D)

> "スケーラビリティは『大規模 CLAUDE.md』でなく『subagent + skill + hook』の組み合わせで実現する。"

**harness-forge での反映**: CLAUDE.md は**ポインタ主義**を徹底し、実質ルールは settings.json の hooks + `.claude/hooks/*.sh` + `.claude/subagents/*.md` に配置。CLAUDE.md から参照される形にする。

### 2.12 **`<important if="..."/>` 条件付きロード** (D)

monorepo や大規模プロジェクトで、CLAUDE.md セクションを条件付きで展開できる。

**harness-forge での反映**: MVP では採用せず、Phase 8 の production-saas / ml-data で検討（monorepo 対応時）。

### 2.13 **revfactory/harness との差別化** (E)

**共通点**:

- ドメイン記述 → チーム構成生成
- Progressive disclosure でスキル生成
- L3 メタレイヤー配置（harness を生成する工場）

**harness-forge の差別化**:
| 側面 | revfactory/harness | harness-forge |
|---|---|---|
| 入力 | 自由記述ドメイン | **構造化 profile.json** (interview 経由) |
| Archetype | ドメイン分析から動的 | **4固定アーキタイプ** (daily-utility / SaaS / ML / design) |
| 出力構造 | agents + skills | **CLAUDE.md + subagents + hooks + skills + settings.json permissions + validation workflow** |
| Validator | 言及なし | **独立 skill として scaffold 後の整合性検査** |
| Locale | 英語前提 | **JA 主戦場** (MVP) |

→ revfactory/harness は「より自由度高・抽象度高」、harness-forge は「**より opinionated・scaffold 成果物が具体的**」。両立可能な補完関係。

---

## 3. 採用しないパターン（理由付き）

### 3.1 ❌ **Role-based Subagents** (HumanLayer が反対、Chachamaru127/shanraisshan は一部提案するが却下)

- "frontend-engineer", "backend-engineer", "data-analyst" 等
- **理由**: HumanLayer の実証通り機能しない。ツール競合が増える。コンテキスト汚染も悪化。
- harness-forge は **Task-type（review / test / research）** で統一する。

### 3.2 ❌ **"Breezing" / 全自動実行モード** (Chachamaru127 A)

- `/harness-work all` のような「承認→実装→レビュー→コミット」ワンコマンド自動化
- **理由**: MVP 範囲外。Phase 8+ で検討だが、少なくとも MVP では user approval gate を残す設計。

### 3.3 ❌ **Dual-IDE モード（Cursor ↔ Claude Code 同期）** (Chachamaru127 A)

- **理由**: デュアル管理の複雑性が payoff を上回る。harness-forge は Claude Code 単一最適化。

### 3.4 ❌ **Codex CLI / OpenAI モデル統合** (Chachamaru127 A)

- **理由**: vendor lock-in を招く。harness-forge は**Claude 単一最適化で統一性を保つ**（ユーザーの現環境では Codex が使えるが、scaffold する harness 自体にはベンダー中立性を維持）。

### 3.5 ❌ **Slides / Video 生成機能** (Chachamaru127 A)

- **理由**: コア開発サイクルと離れた周辺機能。Google AI API や Remotion の依存が重い。

### 3.6 ❌ **Prompt-only 品質管理** (B, C)

- 「CLAUDE.md に'テストを書いてね'と書く」
- **理由**: 機能しないことが実証済み。全ての quality gate は hook か CI で機械強制する。

### 3.7 ❌ **説明的ドキュメント（README / design docs）の蓄積** (B)

- **理由**: ドキュメントは陳腐化（rot）する。テスト・ADR・型定義を「真実」の拠り所にする。
- harness-forge の scaffold では `docs/architecture.md` を置くが**最小限**、詳細はコード+テストに委ねる。

### 3.8 ❌ **Full Test Suite Execution at Every Turn** (C)

- **理由**: context 汚染 + タスク忘却 + 幻覚を招く。
- harness-forge の pre-commit は**差分テスト**デフォルト、full test は CI に任せる。

### 3.9 ❌ **大量の Skill / MCP Preload** (C)

- 「念のため」の事前読み込み
- **理由**: instruction budget を浪費し、primacy bias を悪化させる。
- harness-forge の subagent テンプレでは `skills:` preload は最小限（reviewer は skill preload 0）。

### 3.10 ❌ **RAG / Vector DB** (D)

- "agentic search" (glob + grep) の方が優位
- **理由**: Claude Code の tools は既に十分。追加の vector store はオーバーヘッド。
- harness-forge では**推奨しない**（将来 ml-data archetype でも不要、むしろ avoid）。

### 3.11 ❌ **`dangerously-skip-permissions`** (D)

- **理由**: wildcards の方が安全。Auto mode や specific allowlist で代替。

### 3.12 ❌ **Premature Optimization / Infrastructure Overbuild** (B, C)

- 実際の失敗を見る前に harness 設計を完成させようとする
- **理由**: 過剰設計のコストが利益を上回る。iteration-driven に徹する。
- → harness-forge の profiler では 2-3 分のインタビューで済ませ、最小 harness から iteration させる。

### 3.13 ❌ **Role-Based Playbook としての巨大 CLAUDE.md** (B, C, D)

- "200 行のコーディングルール集"
- **理由**: 半分無視される（primacy bias）。50-60 行ポインタ主義徹底。

---

## 4. 架構パターン（revfactory/harness から抽出）

6つのオーケストレーション・パターン。harness-forge の subagent 設計時に参照。

| パターン                        | 説明                  | 採用時期                                          |
| --------------------------- | ------------------- | --------------------------------------------- |
| **Pipeline**                | 順序依存タスク (A → B → C) | production-saas (Plan→Work→Review)            |
| **Fan-out / Fan-in**        | 並列独立タスク             | ml-data (複数モデル並列評価)                           |
| **Expert Pool**             | コンテキスト依存の選別呼び出し     | design-heavy (ui-reviewer / a11y-reviewer 切替) |
| **Producer-Reviewer**       | 生成 → 品質審査           | 全 archetype (reviewer subagent)               |
| **Supervisor**              | 中央エージェントによる動的分配     | MVP 範囲外（Agent teams 相当）                       |
| **Hierarchical Delegation** | トップダウン再帰的委譲         | MVP 範囲外（subagent ネスト不可制約）                     |

**MVP 採用**: Producer-Reviewer のみ。他は archetype 拡張時または Phase 8+。

---

## 5. 実装的示唆サマリー（harness-forge のテンプレ設計へ）

### 5.1 daily-utility テンプレに組み込む

- ✅ CLAUDE.md ≤50 行（pointer-only）
- ✅ PostToolUse auto-format hook
- ✅ pre-commit lint hook
- ✅ 単一 `reviewer` subagent (task-type, tools: Read/Grep/Bash(readonly))
- ✅ Producer-Reviewer パターン
- ✅ hook stderr: 成功は黙る、失敗のみ `WHY + FIX` 形式で出す

### 5.2 production-saas テンプレで追加

- ✅ `code-reviewer` / `security-reviewer` / `test-author` subagents (全 task-type)
- ✅ PreToolUse: linter 設定ファイル保護 hook
- ✅ PreToolUse: secret 漏洩ブロック hook
- ✅ CI YAML (GitHub Actions): typecheck + test + security-scan
- ✅ Pipeline パターン (Plan → Work → Review)

### 5.3 ml-data テンプレで追加

- ✅ `notebook-reviewer` / `data-validator` subagents
- ✅ PreToolUse: >50MB artifact ブロック hook
- ✅ `.gitattributes` で notebook diff filter
- ✅ Fan-out / Fan-in パターン（データ品質 → モデル評価 → 観測の6層 [B]）

### 5.4 design-heavy テンプレで追加

- ✅ `ui-reviewer` / `a11y-reviewer` subagents
- ✅ PostToolUse: screenshot hook（gstack / Playwright があれば）
- ✅ E2E via accessibility tree (token 効率 90% 削減 [B])
- ✅ Expert Pool パターン

### 5.5 全 archetype 横断

- ✅ error message に `WHY / FIX` 埋め込み
- ✅ 成功は無言・失敗のみ出力
- ✅ linter 設定ファイル保護
- ✅ iteration-driven (事前最適化禁止)

---

## 6. 未解決・将来調査

- Plankton パターン（20+ linter 統合）の具体実装 → Phase 8+ の production-saas 拡張時
- ADR (Architecture Decision Record) + archgate の具体構造 → Phase 8+ で検討
- Claude Code on the web / Agent Teams の harness 最適化 → MVP 範囲外
- 長期運用での harness evolution メカニズム（revfactory/harness の「進化メカニズム」相当）→ 将来の `harness-evolver` 第4 skill として分離検討
