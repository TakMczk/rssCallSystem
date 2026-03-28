# RSS Call System

技術記事を自動収集し、AI（GPT-5-nano）で評価・ランキングして RSS フィードと Web UI 用データを生成するシステムです。

## 特徴

- 🚀 **高速**: GPT-5-nanoで63%高速化（21秒/25記事）
- 💰 **低コスト**: gpt-4o-miniから67%コスト削減
- 🎯 **高品質**: 6次元スコアリング（新規性、興味性、専門性、文化関連性、生活接続性、創造性）
- 🧭 **ハイブリッド順位づけ**: LLM総合点に鮮度ボーナスとソース多様性ペナルティを加味
- 🗂️ **Web UI**: Material UI ベースのカード表示で、要約・スコア・評価理由を一覧化
- 📊 **バッチ処理**: BATCH_SIZE=20で効率的なAPI呼び出し
- 🔄 **キャッシング**: スコア結果をキャッシュして重複処理を削減

## システム構成

```
src/
├── config.py         # 設定管理
├── fetcher.py        # RSS記事取得
├── scorer.py         # AI評価（GPT-5-nano）
├── ranking.py        # ランキング生成
├── json_builder.py   # Web UI 向け JSON 構築
├── rss_builder.py    # RSS構築
└── main.py          # メインエントリーポイント

web/
├── src/             # React + TypeScript + MUI フロントエンド
└── dist/            # Vite ビルド出力（docs/ へ同期）
```

## 必要要件

- Python 3.9+
- OpenAI API Key（GPT-5-nanoアクセス権）

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/rssCallSystem.git
cd rssCallSystem
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
cd web && npm install
```

### 3. 環境変数の設定

`.env`ファイルを作成し、以下を設定：

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_ORGANIZATION=your_org_id_here  # Optional

# Model Configuration (optional)
OPENAI_MODEL=gpt-5-nano  # Default

# RSS reader compatibility (optional)
# If your reader hides items as duplicates (e.g. Inoreader duplicate filters),
# this makes each item's <link> unique by appending a stable query param.
RSS_DEDUPLICATE_LINKS=true
RSS_DEDUP_PARAM_KEY=rcs_id
```

## 使い方

### システムの実行

```bash
python -m src.main
```

または、提供されているタスクを使用：

```bash
# 依存関係のインストール
pip install -r requirements.txt

# システムの実行
python -m src.main

# テストの実行
python -m pytest tests/ -v

# クリーンアップ
find . -name '*.pyc' -delete && find . -name '__pycache__' -type d -exec rm -rf {} +
```

### 出力

生成物は以下に保存されます。

- `docs/rss.xml` - RSS フィード
- `docs/data.json` - Web UI 用データ
- `docs/index.html`, `docs/assets/**` - Web UI

## 既定の収集フィード

既定では以下の技術系フィードを巡回します。

- `https://zenn.dev/feed`
- `https://codezine.jp/rss/new/20/index.xml`
- `https://qiita.com/popular-items/feed`
- `https://www.publickey1.jp/atom.xml`
- `https://hnrss.org/best`
- `https://lobste.rs/rss`
- `https://feeds.arstechnica.com/arstechnica/index`
- `https://www.theverge.com/rss/index.xml`
- `https://www.technologyreview.jp/feed/`
- `https://feeds.japan.zdnet.com/rss/zdnet/all.rdf`
- `https://wirelesswire.jp/feed/`
- `https://wired.jp/rssfeeder/`
- `https://xenospectrum.com/feed/`
- `https://tech.nikkeibp.co.jp/rss/xtech-it.rdf`
- `https://b.hatena.ne.jp/hotentry/it.rss`

## GPT-5-nanoへの移行

### なぜGPT-5-nano？

| 項目 | gpt-4o-mini | gpt-5-nano | 改善 |
|-----|------------|-----------|------|
| 入力コスト | $0.15/1M | $0.05/1M | **67%削減** |
| 出力コスト | $0.60/1M | $0.40/1M | **33%削減** |
| 処理速度 | 2.33秒/記事 | 1.42秒/記事 | **39%高速化** |
| Context | 128K | 400K | **3.1倍** |
| Max Output | 16K | 128K | **8倍** |

### 重要な実装ポイント

GPT-5-nanoは**reasoning model**です。分類タスクでは `reasoning_effort="minimal"` を使用することで、reasoning tokensを0に抑え、コストと速度を最適化できます。

```python
response = await client.chat.completions.create(
    model="gpt-5-nano",
    messages=[...],
    reasoning_effort="minimal",  # 重要: 0 reasoning tokens
    max_completion_tokens=1024,
    response_format={"type": "json_object"}
)
```

詳細は [GPT-5移行ガイド](docs/GPT5_MIGRATION.md) を参照してください。

## スコアリング基準

各記事は以下の6つの次元で0-10点評価されます：

| 次元 | 説明 | 重み |
|-----|------|------|
| 新規性 (Novelty) | 新しい技術・アイデアの度合い | Tech 合算に寄与 |
| 興味性 (Interest) | 読者の関心を引く度合い | Tech 合算に寄与 |
| 専門性 (Expertise) | 技術的深さ・詳細度 | Tech 合算に寄与 |
| 文化関連性 (Cultural Relevance) | 文化・社会への影響 | Culture 合算に寄与 |
| 生活接続性 (Lifestyle Connection) | 日常生活への関連性 | Culture 合算に寄与 |
| 創造性 (Creativity) | 独創的なアプローチ | Culture 合算に寄与 |

**合計**: 60点満点（Tech 40点相当 + Culture 20点相当）

## ランキング方式

現在の並び順は、単純な総合点ソートではなく次のハイブリッド方式です。

1. `ScoreResult.total` をベーススコアとして使用
2. 公開時刻に応じて鮮度ボーナスを追加
3. 同一ソースが上位を占有しすぎないよう、選抜時にソフトな repeat penalty を適用

この設計は Reddit / Hacker News / Lobsters の time-decay 発想と、NewsBlur の「偏りを明示的に制御する」考え方を、小さく deterministic に取り入れたものです。

## パフォーマンス

### 実測データ（25記事）

```
処理時間: 35.41秒
API呼び出し: 2回（BATCH_SIZE=20）
1記事あたり: 1.42秒
成功率: 100%（25/25記事）
```

### コスト見積もり

```
25記事 × 2バッチ × ~170 tokens/記事 = ~4250 tokens
Input: 4250 × $0.05/1M = $0.0002
Output: 2500 × $0.40/1M = $0.001
合計: ~$0.0012/25記事（約$0.00005/記事）
```

## テスト

```bash
# 全テストの実行
./.venv/bin/python -m pytest -q

# 特定のテストの実行
python -m pytest tests/test_ranking.py -v

# フロントエンドのビルド
cd web && npm run build

# 統合テスト
python test_integrated.py
```

## Web UI のビルド

フロントエンドを変更したときは `web/` でビルドし、`docs/` へ同期します。

```bash
cd web
npm run build:pages
```

このコマンドは `web/dist` を生成したあと、`docs/index.html` と `docs/assets/**` のみを更新します。`docs/rss.xml`、`docs/data.json`、`docs/images/**`、`docs/*.md` は保持されます。

### 注意事項

- **`web/` を変更した場合**は、push 前に必ず `cd web && npm run build:pages` を実行してください
- `main` / `docs` 配信なので、**生成済みの `docs/index.html` と `docs/assets/**` もコミット対象**です
- 定期 GitHub Actions は RSS / JSON 更新が主目的で、**フロントエンドの再ビルド前提ではありません**
- Python 側だけを変更した場合は、通常どおり `python -m src.main` による `docs/rss.xml` / `docs/data.json` 更新で運用できます

## アーキテクチャの特徴

### 1. バッチ処理の最適化

- BATCH_SIZE=20で複数記事を一度にスコアリング
- API呼び出しを50%削減

### 2. エラーハンドリング

- リトライメカニズム（MAX_SCORE_RETRY=2）
- 部分的な失敗に対する堅牢な処理
- 詳細なログ記録

### 3. キャッシング

- JSONLファイルでスコア結果をキャッシュ
- `SCORER_CACHE_VERSION` をキーに含め、rubric変更時の stale cache 再利用を防止
- 同じ記事の再スコアリングを回避

### 4. 柔軟な設定

- 環境変数で簡単にカスタマイズ
- モデル、バッチサイズ、RSS設定など

## トラブルシューティング

### 空のレスポンスが返る

**症状**: GPT-5-nanoが空の応答を返す

**解決策**: `reasoning_effort="minimal"` が設定されているか確認

```python
reasoning_effort="minimal"  # これが必須
```

### temperature エラー

**症状**: `temperature is not supported for this model`

**解決策**: GPT-5-nanoでは `temperature`, `top_p`, `logprobs` はサポートされていません。これらのパラメータを削除してください。

### レート制限エラー

**症状**: `RateLimitError: Rate limit exceeded`

**解決策**:

1. `BATCH_SIZE` を小さくする（例: 10）
2. リトライ間隔を長くする
3. OpenAIのTierをアップグレードする

詳細は [GPT-5移行ガイド](docs/GPT5_MIGRATION.md) を参照してください。

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します！大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 参考資料

- [GPT-5-nano Model Page](https://platform.openai.com/docs/models/gpt-5-nano)
- [GPT-5 Usage Guide](https://platform.openai.com/docs/guides/gpt-5)
- [Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)
- [Reasoning Guide](https://platform.openai.com/docs/guides/reasoning)
