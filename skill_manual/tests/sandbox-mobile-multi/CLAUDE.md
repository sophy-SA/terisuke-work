# sandbox-multi-platform

React Native + iOS + Android の3プラットフォームを同時運用するアプリ

## モバイル開発ワークフロー

対応プラットフォーム: **react-native,ios,android**

### 起動時ルーチン

1. `pwd` で作業ディレクトリ確認
2. `git log --oneline -10` で最近のコミット確認
3. 既存ビルド失敗・失敗テストを先に修正してから新機能
4. UI 編集時は Simulator/Emulator を起動してから作業

### ビルド・テストコマンド

- **iOS**: `xcodebuild -scheme <Scheme> build` / `xcodebuild test -scheme <Scheme>`
- **Android**: `./gradlew build` / `./gradlew connectedAndroidTest`
- **React Native**: `npx react-native run-ios|run-android` / `npm test`


### 作業ルール

- 一度に1画面・1 feature に集中 (incremental progress)
- 変更後は `mobile-reviewer` subagent にレビュー依頼 → commit
- UI 変更は Simulator/Emulator で目視確認してから commit
- 行き詰まりは `/clear`、状態復元は `/rewind`

## プロジェクト固有

- **言語**: typescript,swift,kotlin
- **意図1**: iOS/Android 両方の manifest を同期させる
- **意図2**: native module bridge の async 漏れを防ぐ
- **意図3**: UI 変更は必ず両 platform の Simulator/Emulator で確認

## 参照

- レビュー観点: `.claude/subagents/mobile-reviewer.md`
- 署名情報漏洩ブロック: `.claude/hooks/block-signing-secret.sh`
- Manifest 編集警告: `.claude/hooks/protect-manifest.sh`
- 説明: `docs/harness.md`

## 禁止事項

- 署名関連ファイル (*.p12 / *.jks / *.keystore / *.mobileprovision / keystore.properties / GoogleService-Info.plist / google-services.json) の commit
- Info.plist / AndroidManifest.xml / app.json / pubspec.yaml の黙って編集 (差分レビュー必須)
- 本番署名での local release build を CI なしで実施
- `--no-verify` でのコミット
