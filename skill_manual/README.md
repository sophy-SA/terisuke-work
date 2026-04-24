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
| `library-package` | npm / PyPI / crates / go module として公開するライブラリ | 計画中 |
| `production-saas` | Next.js / Supabase 等、認証・決済を伴う商用アプリ | 計画中 |
| `mobile-app` | iOS / Android / React Native / Flutter のモバイルアプリ | ✅ |
| `ml-data` | Jupyter + pytest + DVC/MLflow 等の ML パイプライン | 計画中 |
| `infra-iac` | Terraform / Ansible / K8s manifests / Helm chart | 計画中 |

デザイン品質を主眼にする場合は、どの archetype でも `project.design_focus: true` フラグを立てることで、UI/a11y レビュアーと関連 hook が自動追加されます (旧 `design-heavy` archetype の後継)。

## インストール

### Quick install (推奨)

```bash
git clone <harness-forge-repo-url> ~/harness-forge   # 任意のパスに clone
bash ~/harness-forge/install.sh                      # ~/.claude/skills/ に symlink
```

Claude Code を再起動すると `/harness-profiler`, `/harness-generator`, `/harness-validator` の 3 skill がメニューに出現します。

### 確認

```
/agents              # Library タブで 3 skill が見えるか確認
```

### アンインストール

```bash
bash ~/harness-forge/uninstall.sh
```

### 高度な設定

- repo を移動した場合: `export HARNESS_FORGE_ASSETS=/new/path/to/harness-forge/assets`
- symlink でなく copy で install したい場合: `bash install.sh --copy`
- scripts を直叩きで使いたい場合 (skill 経由でなく): `python3 /path/to/harness-forge/skills/harness-generator/scripts/apply_scaffold.py --profile ./profile.json`

### 前提

- Python 3.10+
- Claude Code が 1 回以上起動済み (`~/.claude/` が存在)
- 推奨: `pip install jsonschema pyyaml` (より厳密な schema 検証 + YAML batch mode 用)

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
