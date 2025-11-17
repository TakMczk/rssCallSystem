# VS Code Markdown エディタ設定ガイド

このワークスペースは、Markdown編集に最適化された設定になっています。

## インストール済み拡張機能

以下の拡張機能がインストールされています:

1. **Markdown All in One** - 包括的なMarkdown編集サポート
   - 目次の自動生成・更新
   - テーブルのフォーマット
   - リストの自動整形
   - キーボードショートカット

2. **Markdown Lint** - Markdownの品質チェック
   - リアルタイムで構文をチェック
   - ベストプラクティスの提案

3. **Markdown Preview Mermaid Support** - Mermaid図表のプレビュー
   - フローチャート、シーケンス図などの表示

4. **Paste Image** - 画像の簡単な挿入
   - クリップボードから画像を直接貼り付け
   - 自動で `docs/images/` に保存

## 主な機能

### エディタ機能

- **自動折り返し**: 長い行を自動的に折り返し
- **フォーマット**: 保存時に自動フォーマット
- **行番号表示**: 編集しやすいように表示
- **ルーラー**: 80文字と120文字の位置にガイド表示

### プレビュー機能

- **サイドバイサイドプレビュー**: `Cmd+K V`
- **フルプレビュー**: `Cmd+Shift+V`
- **スクロール同期**: エディタとプレビューが連動
- **ダブルクリックで編集**: プレビューから編集画面へジャンプ

### スニペット

以下のプレフィックスを入力して、`Tab`キーでスニペットを展開できます:

- `code` - コードブロック
- `task` - タスクリスト
- `table` - テーブル
- `link` - リンク
- `img` - 画像
- `alert-info` - 情報アラート
- `alert-warning` - 警告アラート
- `alert-danger` - 重要アラート
- `details` - 折りたたみセクション
- `frontmatter` - Frontmatter
- `mermaid-flow` - Mermaidフローチャート
- `mermaid-seq` - Mermaidシーケンス図
- `hr` - 水平線
- `footnote` - 脚注

### キーボードショートカット

- `Cmd+K V` - サイドプレビューを開く
- `Cmd+Shift+V` - プレビューを開く
- `Cmd+Shift+F` - テーブルをフォーマット
- `Cmd+Shift+T` - 目次を更新
- `Cmd+Shift+C` - チェックボックスを切り替え
- `Cmd+Shift+L` - リストを切り替え

## 画像の挿入方法

1. 画像をクリップボードにコピー
2. Markdownファイルで挿入したい位置にカーソルを置く
3. `Cmd+Alt+V` (または右クリック→「Paste Image」)
4. 自動的に `docs/images/` に保存され、リンクが挿入されます

## Markdownlint設定

以下のルールが調整されています:

- `MD013` (行の長さ制限) - 無効化
- `MD024` (重複する見出し) - 許可
- `MD033` (HTMLタグ) - 許可
- `MD041` (最初の行が見出し) - 不要

より厳密にしたい場合は `.markdownlint.json` を編集してください。

## 目次の自動生成

1. 目次を挿入したい位置に以下を記述:

   ```markdown
   <!-- TOC -->
   <!-- /TOC -->
   ```

2. 保存すると自動的に目次が生成されます

または、コマンドパレット (`Cmd+Shift+P`) から「Markdown All in One: Create Table of Contents」を実行します。

## Mermaid図の作成例

### フローチャート

\`\`\`mermaid
graph TD
    A[開始] --> B{条件}
    B -->|Yes| C[処理1]
    B -->|No| D[処理2]
    C --> E[終了]
    D --> E
\`\`\`

### シーケンス図

\`\`\`mermaid
sequenceDiagram
    participant User
    participant System
    User->>System: リクエスト
    System-->>User: レスポンス
\`\`\`

## トラブルシューティング

### プレビューが表示されない

- 拡張機能が有効になっているか確認
- VS Codeを再起動

### 画像が貼り付けられない

- `docs/images/` ディレクトリが存在するか確認
- Paste Image拡張機能が有効か確認

### Lintエラーが多すぎる

- `.markdownlint.json` でルールを調整
- 特定のルールを無効化: `"MD000": false`

## 参考リンク

- [Markdown All in One](https://marketplace.visualstudio.com/items?itemName=yzhang.markdown-all-in-one)
- [Markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint)
- [Mermaid Documentation](https://mermaid-js.github.io/mermaid/)
