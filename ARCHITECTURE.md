# システムアーキテクチャ

## 概要

RSS Call Systemは、複数のRSSフィードから技術記事を収集し、AI（GPT-5-nano）で評価・ランキングして、高品質な記事のみを含むRSSフィードを生成するシステムです。

## システム構成

```
┌─────────────┐
│ RSS Sources │ 
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Fetcher    │ (src/fetcher.py)
│  記事取得   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Scorer    │ (src/scorer.py)
│ GPT-5-nano  │ reasoning_effort="minimal"
│ 6次元評価   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Ranking    │ (src/ranking.py)
│ スコアソート │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ RSS Builder │ (src/rss_builder.py)
│ XML生成     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ docs/rss.xml│
└─────────────┘
```

## コンポーネント

### 1. Fetcher (src/fetcher.py)

**役割**: 複数のRSSフィードから記事を取得

**機能**:

- 非同期HTTP通信（httpx）
- RSS/Atomパース（feedparser）
- エラーハンドリングとリトライ
- 重複記事の除外

**出力**: `List[Article]`

### 2. Scorer (src/scorer.py)

**役割**: GPT-5-nanoを使用した記事評価

**機能**:

- **バッチ処理**: 6記事以上は20件ずつバッチ処理（API呼び出し50%削減）
- **個別処理**: 5記事以下は個別にスコアリング
- **キャッシング**: JSONLファイルでスコア結果を保存
- **6次元評価**:
  - 新規性 (Novelty): 0-10点
  - 興味性 (Interest): 0-10点
  - 専門性 (Expertise): 0-10点
  - 文化関連性 (Cultural Relevance): 0-10点
  - 生活接続性 (Lifestyle Connection): 0-10点
  - 創造性 (Creativity): 0-10点

**重要パラメータ**:

```python
model="gpt-5-nano"
reasoning_effort="minimal"  # 0 reasoning tokens
max_completion_tokens=1024  # Single
max_completion_tokens=16384 # Batch
response_format={"type": "json_object"}
```

**出力**: `Dict[str, ScoreResult]`

### 3. Ranking (src/ranking.py)

**役割**: スコアに基づく記事のソート

**機能**:

- 合計スコア（60点満点）で降順ソート
- Tech Score (30点) = 新規性 + 興味性 + 専門性
- Culture Score (30点) = 文化関連性 + 生活接続性 + 創造性

**出力**: `List[ScoredArticle]`

### 4. RSS Builder (src/rss_builder.py)

**役割**: ランク付けされた記事からRSS 2.0フィードを生成

**機能**:

- RSS 2.0形式のXML生成
- 記事の説明にスコア詳細を追加
- カテゴリー・タグの保持

**出力**: `docs/rss.xml`

## データモデル

### Article (src/models.py)

```python
@dataclass
class Article:
    title: str
    link: str
    published: datetime
    source: str
    summary: str
    excerpt: str
    category: Optional[str]
    tags: List[str]
```

### ScoreResult (src/models.py)

```python
@dataclass
class ScoreResult:
    novelty: int           # 新規性 0-10
    interest: int          # 興味性 0-10
    expertise: int         # 専門性 0-10
    cultural_relevance: int   # 文化関連性 0-10
    lifestyle_connection: int # 生活接続性 0-10
    creativity: int        # 創造性 0-10
    reason: str            # スコア理由
    
    @property
    def tech_score(self) -> int:
        return self.novelty + self.interest + self.expertise
    
    @property
    def culture_score(self) -> int:
        return self.cultural_relevance + self.lifestyle_connection + self.creativity
    
    @property
    def total_score(self) -> int:
        return self.tech_score + self.culture_score
```

## パフォーマンス最適化

### 1. バッチ処理

- **BATCH_SIZE=20**: 20記事ずつまとめてスコアリング
- **効果**: API呼び出しを50%削減（例: 25記事 → 2回のAPI呼び出し）

### 2. GPT-5-nano + reasoning_effort="minimal"

- **reasoning tokens = 0**: 推論トークンなしで分類
- **効果**: コスト67%削減、速度63%高速化

### 3. キャッシング

- **ファイル**: `.cache/scores.jsonl`
- **キー**: `title + published` のハッシュ
- **効果**: 同じ記事の再スコアリングを回避

### 4. 非同期処理

- **httpx**: 非同期HTTPクライアント
- **asyncio**: 並行記事取得・スコアリング

## 実測パフォーマンス

| 指標 | gpt-4o-mini | gpt-5-nano | 改善 |
|-----|-------------|-----------|------|
| 処理時間（25記事） | 58秒 | 21秒 | **63%高速化** |
| API呼び出し | 2回 | 2回 | 同じ |
| 入力コスト | $0.15/1M | $0.05/1M | **67%削減** |
| 出力コスト | $0.60/1M | $0.40/1M | **33%削減** |
| Context | 128K | 400K | **3.1倍** |
| Max Output | 16K | 128K | **8倍** |

## 設定

### 環境変数（.env）

```bash
# OpenAI API
OPENAI_API_KEY=your_api_key
OPENAI_ORGANIZATION=your_org_id  # Optional

# Model Configuration
OPENAI_MODEL=gpt-5-nano  # Default

# RSS Configuration
RSS_TITLE="厳選技術記事フィード"
RSS_DESCRIPTION="AIが評価した高品質な技術記事"
RSS_LANGUAGE="ja"
SITE_BASE_URL=https://example.com/

# Scoring
BATCH_SIZE=20
MAX_SCORE_RETRY=2
```

### config.py

```python
OPENAI_MODEL: str = "gpt-5-nano"
BATCH_SIZE: int = 20
RETRY_MAX: int = 2
```

## エラーハンドリング

### 1. リトライメカニズム

- **MAX_SCORE_RETRY=2**: 最大2回リトライ
- **対象**: API呼び出し失敗、ネットワークエラー
- **戦略**: 指数バックオフ

### 2. 部分的失敗の処理

- **バッチスコアリング**: 一部失敗しても残りの記事は処理
- **個別スコアリング**: 失敗した記事はスキップ

### 3. ログ記録

- **logging**: INFO/WARNING/ERRORレベル
- **出力**: 標準出力 + ファイル（オプション）

## 今後の拡張

### 短期

- ✅ GPT-5-nano移行完了
- ✅ バッチ処理最適化完了
- [ ] GitHub Actions ワークフローの更新

### 中期

- [ ] Responses API への移行（より高度な推論が必要な場合）
- [ ] プロンプトキャッシングの活用
- [ ] verbosityパラメータの活用

### 長期

- [ ] GPT-5.2への移行
- [ ] マルチモーダル対応（画像解析）
- [ ] リアルタイム更新

## セキュリティ

### 1. API Key管理

- **環境変数**: `.env`ファイル（Gitignore）
- **GitHub Secrets**: CI/CD環境

### 2. レート制限

- **OpenAI Tier 1**: 500 RPM, 200K TPM
- **推定使用量**: ~20% (25記事/2バッチ)

### 3. 入力検証

- **記事データ**: XSS対策、サニタイゼーション
- **URL検証**: スキーム・ホストチェック

## 参考資料

- [GPT-5移行ガイド](docs/GPT5_MIGRATION.md)
- [移行サマリー](docs/MIGRATION_SUMMARY.md)
- [デプロイ手順](DEPLOYMENT.md)
- [OpenAI GPT-5-nano](https://platform.openai.com/docs/models/gpt-5-nano)
