# Severity Policy

チェックを ERROR / WARNING / INFO に振り分ける基準。

## 判定フロー

```
このチェックが失敗すると何が起こる?
  ├── harness が動かない / Claude Code が起動エラー / ユーザー呼び出し時に明示的エラー
  │     → ERROR
  ├── harness は動くが、Anthropic 公式または実証済み研究が「悪影響」と示している
  │     → WARNING
  └── スタイル・将来的な改善余地・軽微な冗長
        → INFO
```

## ERROR の例

- C04: 参照 hook script が存在しない → hook 発火時に Claude Code エラー
- C07: subagent tools に未知名 → 動かない
- C08: CLAUDE.md 参照 subagent が無い → ユーザー呼び出し時エラー
- C10: 秘密情報検出 → セキュリティインシデント
- C12: settings.json パースエラー → Claude Code 起動不良

## WARNING の例

- C01: CLAUDE.md 50 行超 → 公式が「無視される」と警告している範囲
- C02: トークン数超過 → primacy bias 悪化 (IFScale 研究)
- C05: hook matcher 重複 → 実害はないが意図しない動作リスク
- C06: write 許可に guard 無し → 危険だが即座の被害なし
- C09: required_checks の ghost → 宣言と実態の乖離
- C13: handles_secrets 宣言に対し hook 無し → 論理的不整合

## INFO の例

- C03: 長い単一散文ブロック → ポインタ主義から外れているが動作問題なし
- C11: shellcheck 違反 → shell スクリプト品質、hook 動作には影響薄

## 禁止事項

- severity を環境依存で変えない (同じ条件なら同じ severity)
- ERROR を WARNING に勝手に downgrade しない
- WARNING を ERROR に勝手に escalate しない
- 重複チェック (同じ事象を複数 ID で報告) を作らない

## 将来の拡張

- ユーザー設定で C01 の閾値を 50 → 80 に変更可能にする (既に CLI 引数で対応)
- `--fail-on WARNING` フラグで CI から WARN も error 扱いにする (Phase 8+)
- `--apply-fixes` で自動修正可能なもの (C03 の散文分離、C05 の matcher 統合) を実施 (Phase 8+)
