# このプロジェクトの Claude Code ハーネス (mobile-app)

**生成元**: harness-forge (archetype: mobile-app)
**対応プラットフォーム**: ios

## 何が scaffold されたか

daily-utility archetype の基本セットに加えて、モバイル固有のファイルが配置されました:

| ファイル | 役割 |
|---|---|
| `CLAUDE.md` | モバイル開発ワークフロー (起動ルーチン、プラットフォーム別ビルドコマンド) |
| `.claude/subagents/mobile-reviewer.md` | モバイル専門レビュアー (iOS/Android/RN/Flutter 観点) |
| `.claude/subagents/reviewer.md` | 汎用コードレビュアー (daily-utility 継承) |
| `.claude/hooks/block-signing-secret.sh` | 署名ファイル (*.p12, *.jks, mobileprovision 等) の commit ブロック |
| `.claude/hooks/protect-manifest.sh` | Info.plist / AndroidManifest / pubspec 等の編集に警告、危険変更をブロック |
| `.claude/hooks/post-edit-format.sh` | 編集後 auto-format (daily-utility 継承) |
| `.claude/hooks/pre-commit-lint.sh` | pre-commit lint (daily-utility 継承) |

- `.claude/hooks/gate-xcodebuild-release.sh` — iOS release build の local 実行をブロック


## なぜこの構成か

### モバイル固有の harness リスク

モバイルアプリは Web と比べて以下のリスクが段違いに高い:

1. **署名情報の漏洩**: 証明書や keystore が git に入ると、即座にアプリ乗っ取り可能
2. **Manifest の事故**: Bundle Identifier / package name の変更はストア上で別アプリ扱い
3. **ローカル release build**: 手元での release 署名は環境差分によるリリース事故の主因

本 harness はこれらを **機械的に** (prompt ではなく hook で) ガードします。

### 採用しなかった要素 (意図的)

- **xcodebuild / gradle の全コマンドを hook で wrap しない**: debug build や test は日常的に使うため。release 関連のみ gate する
- **Simulator/Emulator 自動起動**: 環境依存が大きいためユーザーに任せる
- **プラットフォーム別に archetype を分けない**: 4 platform 用に 4 archetype は保守負荷、共通 70% は template で吸収

## 増築するには

### セキュリティを強化したい

`profile.json` の `safety.handles_secrets` を true にし、`.harness-forge.state.json` を削除して `/harness-generator` を再実行すると、generic secret block hook も追加されます。

### UI テスト自動化を scaffold したい

将来の Phase 8b+ で `validation/ui-test-runner.sh.tmpl` を提供予定。当面は手動で fastlane / xcodebuild test / gradle connectedAndroidTest を呼んでください。

### archetype を切り替えたい

`profile.json` の `archetype_primary` を変更 (例: 商用リリースなら `production-saas` へ) して再 generate 可能です。

## 検証

scaffold 直後、以下で健全性を確認:

```
/harness-validator
```

`harness-report.md` に結果が出力されます。errors が 0 なら健全。

## 参考資料

- Anthropic: [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- Sakasegawa: [Harness Engineering 2026](https://nyosegawa.com/en/posts/harness-engineering-best-practices-2026/)
- Apple: [Signing & Capabilities](https://developer.apple.com/documentation/xcode/managing-signing-certificates)
- Google: [Sign your app](https://developer.android.com/studio/publish/app-signing)
