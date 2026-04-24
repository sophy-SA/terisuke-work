# sandbox-cli-with-secrets

秘密情報を扱う CLI の fixture。C13 + conditional hook を検証する

## 起動時ルーチン

新しいセッション開始時は以下の順で確認する:

1. `pwd` で作業ディレクトリを確認
2. `git log --oneline -10` で最近のコミットを確認
3. `docs/progress.md` が存在すれば読む
4. **既存のバグ・失敗テストがあれば先に修正**してから新機能に着手

## 作業ルール

- 一度に1つの変更に集中する (incremental progress)
- コミット前に `.claude/hooks/pre-commit-lint.sh` を通す (git pre-commit が自動呼出)
- 変更後は `reviewer` subagent に「このディフを見て」と依頼してから commit
- 行き詰まったら `/clear` でコンテキストをリセット、`/rewind` で状態を戻す

## プロジェクト固有

- **言語**: python
- **意図1**: 秘密情報を誤って commit しない
- **意図2**: 破壊的コマンドは必ず dry-run してから実行
- **意図3**: 

## 参照

- アーキテクチャ: `docs/harness.md` (このハーネスが何をしているか)
- レビュー観点: `.claude/subagents/reviewer.md`
- 自動整形: `.claude/hooks/post-edit-format.sh` (PostToolUse で編集後自動実行)
- lint ゲート: `.claude/hooks/pre-commit-lint.sh` (コミット前に自動実行)

## 禁止事項

- CLAUDE.md をこれ以上肥大化させない (現在の上限: 50 行)。追加ルールは hook で強制するか `docs/` に外出し
- `--no-verify` でのコミット (hook 失敗は根本原因を直す)
