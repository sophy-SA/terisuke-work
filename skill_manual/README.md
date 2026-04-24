# harness-forge

Claude Code の**ハーネス環境**を、利用者のプロジェクトプロファイルに合わせて自動設計・scaffold する Skill ファミリー。

## 何をするか

「ハーネスエンジニアリング」は、CLAUDE.md / subagents / skills / hooks / validation workflow を統合的に設計する実践です。Anthropic 公式ベンチマークでは **harness を変更するだけで SWE-bench +22 ポイント**（同モデルでモデル差し替えは +1 ポイント）が実証されており、モデル選択よりも**遥かに高レバレッジ**な領域です。

しかし、実際の最適解はプロジェクトの性格（日常ツール / 商用 SaaS / ML パイプライン / デザイン重視フロントエンド）で大きく異なります。harness-forge は:

1. **harness-profiler** がインタビューで利用者のプロジェクト属性を聞き取り、`profile.json` を生成
2. **harness-generator** が `profile.json` に基づき、最適な harness 一式を**実ファイルとして scaffold**
3. **harness-validator** が scaffold 後の harness を静的に検査し、CLAUDE.md 肥大・hook 衝突・permissions 不整合を検出

の3つの Skill として実装されています。

## 対象アーキタイプ

| Archetype | 対象プロジェクト | MVP |
|---|---|---|
| `daily-utility` | 個人用 CLI / 日常ツール / shell script | ✅ |
| `production-saas` | Next.js / Supabase 等、認証・決済を伴う商用アプリ | 計画中 |
| `ml-data` | Jupyter + pytest + DVC/MLflow 等の ML パイプライン | 計画中 |
| `design-heavy` | Tailwind / shadcn/ui / デザインレビューフロー中心 | 計画中 |

## インストール

（開発中）リリース後に `~/.claude/skills/` への symlink 方式 or plugin 形式で提供予定。

## 使い方

```
# 1. 対象プロジェクトのディレクトリで:
/harness-profiler          # 2-3 分のインタビュー → profile.json 出力

# 2. 生成された profile.json を確認・編集してから:
/harness-generator         # CLAUDE.md, .claude/*, docs/harness.md 一式を scaffold

# 3. scaffold の整合性チェック:
/harness-validator         # harness-report.md / harness-report.json 出力
```

## リポジトリ構成

```
harness-forge/
├── skills/              # 3 つの Skill 本体
│   ├── harness-profiler/
│   ├── harness-generator/
│   └── harness-validator/
├── assets/              # Skill 横断のテンプレート・知識
│   ├── archetypes/      # アーキタイプ定義 (YAML)
│   ├── templates/       # scaffold 用テンプレート
│   └── knowledge/       # Anthropic 公式 + コミュニティパターンの distilled 台帳
├── tests/               # unit / integration / E2E テスト
└── docs/
    ├── architecture.md  # 3-skill データフロー
    ├── archetypes.md    # アーキタイプ分類ガイド
    └── extending.md     # 新アーキタイプ追加ガイド
```

## ステータス

**フェーズ**: Phase 1 (repo bootstrap) / 2026-04-24 時点
**MVP ターゲット**: daily-utility アーキタイプの end-to-end scaffold
**詳細計画**: `~/.claude/plans/skills-web-claude-md-skills-claude-gpt-replicated-shamir.md` を参照

## 設計原則

- **Anthropic 公式 + コミュニティ実装**をベースラインとする（特定個人の harness を流用しない）
- **Task-type subagents**（Research / Implement / Verify / Review）で統一、role-based（frontend-engineer 等）は採用しない
- **Enforce with mechanisms, not prompts** — 品質ゲートは hook で機械強制、CLAUDE.md のアドバイザリ指示に頼らない
- **CLAUDE.md ≤ 50 行** をポインタ主義で徹底（Sakasegawa 基準）
- **Iteration-driven** — profiler は2-3分の最小インタビューで済ませ、実失敗を見てから harness を強化する

## ライセンス

MIT (予定、要確認)
