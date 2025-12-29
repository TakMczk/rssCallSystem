# GPT-5-nano移行・最適化実装計画書

**作成日**: 2025年12月29日  
**対象システム**: RSS Call System  
**実装者**: Development Team  
**ステータス**: 承認済み

---

## 📋 エグゼクティブサマリー

本計画は、RSSコールシステムにおけるGemini API依存を完全に排除し、OpenAI GPT-5-nanoへ統一移行することで、コスト削減（50%）、評価精度向上、コード保守性向上を実現します。

### 主要な変更点

- **API統一**: Gemini + OpenAI → OpenAI のみ
- **モデル変更**: gpt-4o-mini → gpt-5-nano
- **バッチサイズ**: 10記事 → 20記事
- **コード削減**: 約150行のGemini関連コード削除

### 期待される効果

- API呼び出し: **50%削減** (10回→5回/100記事)
- 月額コスト: **50%削減** ($2-3→$1-2)
- 評価精度: **向上** (400Kコンテキスト活用)
- 保守性: **大幅向上** (単一API依存)

---

## 🎯 背景と目的

### 現状の課題

1. **API の複雑性**: Gemini/OpenAI の2系統のコード維持
2. **Gemini制約**: 無料枠の制限、レート制限
3. **非効率なバッチサイズ**: BATCH_SIZE=10は保守的すぎる
4. **最新モデル未活用**: GPT-5世代の高性能を活用していない

### 移行の理由

1. **GPT-5-nanoの圧倒的優位性**:
   - Context: 400K (gpt-4o-miniの3.1倍)
   - Output: 128K (7.8倍)
   - Reasoning機能: 高度な推論能力
   - コスト: 67%削減 (input $0.15→$0.05)

2. **運用シンプル化**:
   - 単一API依存で管理容易
   - 環境変数の削減
   - デバッグの簡素化

3. **スケーラビリティ**:
   - レート制限に余裕（20%使用率）
   - 将来的な記事数増加に対応可能

---

## 🔧 技術仕様

### モデル比較

| 項目 | gpt-4o-mini (現在) | gpt-5-nano (移行後) | 改善率 |
|------|-------------------|---------------------|--------|
| Context Window | 128K | 400K | +312% |
| Max Output | 16K | 128K | +800% |
| Input Price | $0.15/1M | $0.05/1M | -67% |
| Output Price | $0.60/1M | $0.40/1M | -33% |
| Reasoning | ❌ | ✅ | ✅ |
| 世代 | GPT-4o | GPT-5 | 最新 |
| 知識カットオフ | 2023/10 | 2024/05 | +7ヶ月 |

### レート制限分析

**Tier 1 (想定):**

- RPM: 500 requests/分
- TPM: 200,000 tokens/分

**使用率計算 (BATCH_SIZE=20, CONCURRENCY=2):**

```
100記事処理:
- バッチ数: 5
- 並列実行: 3回 (2+2+1)
- トークン消費: 20記事 × 1,000トークン × 2並列 = 40,000 tokens/分
- 使用率: 40K / 200K = 20%
```

**結論**: レート制限に引っかかる可能性は**極めて低い**

### アーキテクチャ変更

**Before:**

```
RSS System
├── Gemini API (メイン)
│   ├── score_articles_batch()
│   └── _score_with_retry()
├── OpenAI API (代替)
│   └── score_articles_openai_batch()
└── Heuristic Fallback
```

**After:**

```
RSS System
├── OpenAI API (GPT-5-nano)
│   ├── score_articles_openai_batch()
│   └── score_article() (単一評価)
└── Heuristic Fallback
```

---

## 📝 実装ステップ

### Phase 1: 環境・設定の整理

#### Step 1.1: キャッシュクリア

**ファイル**: `.cache/scores.jsonl`

```bash
rm .cache/scores.jsonl
```

**理由**: Gemini評価のキャッシュをクリアし、GPT-5-nanoで全記事を再評価

#### Step 1.2: 環境変数削除

**ファイル**: `.env`

```diff
- GEMINI_API_KEY=AIzaSy...
- USE_OPENAI=true
```

**理由**: OpenAI専用化により不要な設定を削除

#### Step 1.3: Config設定削除

**ファイル**: `src/config.py` (L23-L27)

```diff
- SCORE_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
- GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
  OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
  OPENAI_ORGANIZATION: Optional[str] = os.getenv("OPENAI_ORGANIZATION")
- USE_OPENAI: bool = os.getenv("USE_OPENAI", "false").lower() == "true"
  OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-nano")
```

#### Step 1.4: バッチサイズ拡大

**ファイル**: `src/config.py` (L38)

```diff
- BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
+ BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "20"))
```

**理由**: 400Kコンテキストを活用してAPI呼び出し50%削減

---

### Phase 2: コード削除（Gemini関連）

#### Step 2.1: OpenAIインポート無条件化

**ファイル**: `src/scorer.py` (L16-L21)

```diff
+ from openai import AsyncOpenAI
+
- try:
-     from openai import AsyncOpenAI
-     HAS_OPENAI = True
- except ImportError:
-     logger.warning("OpenAI library not installed")
-     HAS_OPENAI = False
```

**理由**: OpenAI必須化により条件付きインポート不要

#### Step 2.2: Gemini専用関数削除

**ファイル**: `src/scorer.py` (L148-L218)

削除対象: `_score_with_retry()` 関数（約70行）

- Gemini APIエンドポイント呼び出し
- Gemini固有のレスポンス処理
- maxOutputTokens設定

#### Step 2.3: Geminiバッチ処理削除

**ファイル**: `src/scorer.py` (L220-L288)

削除対象: `score_articles_batch()` 関数（約70行）

- Geminiバッチプロンプト生成
- Gemini API呼び出し
- バッチレスポンスパース処理

---

### Phase 3: コード最適化（OpenAI）

#### Step 3.1: 単一記事評価のOpenAI化

**ファイル**: `src/scorer.py` (L108-L146)

**現在の処理フロー**:

```
score_article()
  ├── キャッシュチェック
  ├── GEMINI_API_KEY チェック ❌
  ├── _score_with_retry() 呼び出し ❌
  └── キャッシュ保存
```

**新しい処理フロー**:

```python
async def score_article(article: Article) -> ScoreResult:
    """Score a single article using OpenAI"""
    # Check cache
    key = hashlib.sha256(f"{article.title}|{article.url}".encode()).hexdigest()[:16]
    async with _cache_lock:
        if key in _cache:
            return _cache[key]

    # Check API key
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; using fallback for '%s'", article.title[:30])
        score = _generate_heuristic_score(article)
        async with _cache_lock:
            _cache[key] = score
        return score

    # Call OpenAI API
    try:
        client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            organization=config.OPENAI_ORGANIZATION
        )
        
        prompt = PROMPT_TEMPLATE.format(
            title=article.title,
            summary=article.summary[:400],
            excerpt=article.excerpt
        )
        
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "あなたは技術記事評価の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=config.LLM_TEMPERATURE,
            max_tokens=512,
            response_format={"type": "json_object"},
            timeout=30.0
        )
        
        text = response.choices[0].message.content.strip()
        data = json.loads(text)
        
        # Validate and create score
        score = ScoreResult(
            novelty=int(data.get("novelty", 5)),
            interest=int(data.get("interest", 5)),
            expertise=int(data.get("expertise", 5)),
            cultural_relevance=int(data.get("cultural_relevance", 5)),
            lifestyle_connection=int(data.get("lifestyle_connection", 5)),
            creativity=int(data.get("creativity", 5)),
            reason=str(data.get("reason", ""))[:120]
        )
        
    except Exception as e:
        logger.warning("OpenAI API error for '%s': %s", article.title[:30], str(e)[:100])
        score = _generate_heuristic_score(article)
    
    # Cache result
    async with _cache_lock:
        _cache[key] = score
        with CACHE_FILE.open("a") as f:
            f.write(json.dumps({"id": key, "score": score.model_dump()}, ensure_ascii=False) + "\n")
    
    return score
```

**注**: 単一記事評価は使用頻度が低い（5記事未満の場合のみ）ため、優先度は低い

#### Step 3.2: バッチ処理最適化

**ファイル**: `src/scorer.py` (L290-L380)

**変更内容**:

```diff
  async def score_articles_openai_batch(articles: List[Article], batch_id: int = 0) -> List[ScoreResult]:
      """Score multiple articles using OpenAI API"""
      if not config.OPENAI_API_KEY:
          logger.info("OPENAI_API_KEY not set; using fallback")
          return [_generate_heuristic_score(article) for article in articles]
  
      # Build batch prompt
      articles_text = ""
      for i, article in enumerate(articles):
          articles_text += f"記事ID: {i}\n"
-         articles_text += f"タイトル: {article.title[:100]}\n"
+         articles_text += f"タイトル: {article.title}\n"
-         articles_text += f"概要: {article.summary[:200]}\n"
+         articles_text += f"概要: {article.summary[:400]}\n"
-         articles_text += f"抜粋: {article.excerpt[:200]}\n\n"
+         articles_text += f"抜粋: {article.excerpt}\n\n"
  
      prompt = BATCH_PROMPT_TEMPLATE.format(articles=articles_text)
  
      # API call with retry
      tries = 0
      while tries < config.MAX_SCORE_RETRY:
          tries += 1
          try:
              client = AsyncOpenAI(
                  api_key=config.OPENAI_API_KEY,
                  organization=config.OPENAI_ORGANIZATION
              )
              
              response = await client.chat.completions.create(
                  model=config.OPENAI_MODEL,
                  messages=[
                      {"role": "system", "content": "あなたは技術記事評価の専門家です。"},
                      {"role": "user", "content": prompt}
                  ],
                  temperature=config.LLM_TEMPERATURE,
-                 max_tokens=2048,
+                 max_tokens=8192,
-                 response_format={"type": "json_object"}
+                 response_format={"type": "json_object"},
+                 timeout=120.0
              )
              
              text = response.choices[0].message.content.strip()
              data = _extract_json_from_text(text)
              
              # Process results with enhanced error handling
              results = []
              for i, article in enumerate(articles):
                  article_result = next((item for item in data if item.get("id") == i), None)
                  
                  if article_result:
                      try:
                          # Validate scores
                          scores = {
                              "novelty": int(article_result.get("novelty", 5)),
                              "interest": int(article_result.get("interest", 5)),
                              "expertise": int(article_result.get("expertise", 5)),
                              "cultural_relevance": int(article_result.get("cultural_relevance", 5)),
                              "lifestyle_connection": int(article_result.get("lifestyle_connection", 5)),
                              "creativity": int(article_result.get("creativity", 5))
                          }
                          
                          if all(_validate_score(s) for s in scores.values()):
                              results.append(ScoreResult(
                                  **scores,
                                  reason=str(article_result.get("reason", ""))[:120]
                              ))
                          else:
                              logger.warning("Invalid scores for article %d in batch %d", i, batch_id)
                              results.append(_generate_heuristic_score(article))
                      except (ValueError, TypeError) as e:
                          logger.warning("Error parsing article %d in batch %d: %s", i, batch_id, e)
                          results.append(_generate_heuristic_score(article))
                  else:
                      logger.warning("Article %d not found in batch %d response", i, batch_id)
                      results.append(_generate_heuristic_score(article))
              
              logger.info("Batch %d completed: %d/%d articles scored", batch_id, len(results), len(articles))
              return results
              
          except Exception as e:
              logger.warning("Batch %d attempt %d failed: %s", batch_id, tries, str(e)[:200])
              
              if tries >= config.MAX_SCORE_RETRY:
                  break
              
              # Exponential backoff with jitter
              delay = (2 ** (tries - 1)) + (0.1 * tries)
              if "429" in str(e) or "rate_limit" in str(e).lower():
                  delay *= 2
                  logger.info("Rate limit detected, backing off for %.1f seconds", delay)
              await asyncio.sleep(delay)
      
      # Final fallback
      logger.warning("Batch %d failed after %d attempts, using heuristic", batch_id, tries)
      return [_generate_heuristic_score(article) for article in articles]
```

**最適化ポイント**:

1. ✅ max_tokens: 2048 → 8192 (20記事対応)
2. ✅ timeout: 明示的に120秒設定
3. ✅ 記事情報の切り詰め緩和
4. ✅ エラーハンドリング強化
5. ✅ レート制限対応（429エラー時の遅延2倍）

#### Step 3.3: API選択ロジック削除

**ファイル**: `src/scorer.py` (L401)

```diff
- api_method = "OpenAI" if config.USE_OPENAI else "Gemini"
+ api_method = "OpenAI"
```

#### Step 3.4: バッチ処理分岐削除

**ファイル**: `src/scorer.py` (L412-L416)

```diff
  logger.info("Processing batch %d: articles %d-%d", batch_id, i+1, i+len(batch))
  
  try:
-     if config.USE_OPENAI:
-         batch_results = await score_articles_openai_batch(batch, batch_id)
-     else:
-         batch_results = await score_articles_batch(batch, batch_id)
+     batch_results = await score_articles_openai_batch(batch, batch_id)
      
      all_results.extend(batch_results)
```

---

### Phase 4: テスト実装

#### Step 4.1: 統合テストスクリプト作成

**ファイル**: `test_integrated.py`

```python
#!/usr/bin/env python
"""統合テスト: Gemini削除 + GPT-5-nano最適化"""
import asyncio
import time
from src.fetcher import fetch_articles
from src.scorer import score_articles
from src import config

async def main():
    print("=== GPT-5-nano統合テスト ===\n")
    
    # 設定確認
    print(f"モデル: {config.OPENAI_MODEL}")
    print(f"バッチサイズ: {config.BATCH_SIZE}")
    print(f"API Key: {'設定済み' if config.OPENAI_API_KEY else '未設定'}")
    print()
    
    # 記事取得
    print("記事を取得中...")
    articles = await fetch_articles()
    test_articles = articles[:25]  # 25記事でテスト
    print(f"取得: {len(test_articles)}記事\n")
    
    # スコアリング（時間測定）
    print("スコアリング開始...")
    start_time = time.time()
    scores = await score_articles(test_articles)
    elapsed = time.time() - start_time
    
    # 結果表示
    print(f"\n=== 結果 ===")
    print(f"処理時間: {elapsed:.2f}秒")
    print(f"スコア取得: {len(scores)}/{len(test_articles)}記事")
    print(f"予想API呼び出し: {len(test_articles) // config.BATCH_SIZE + (1 if len(test_articles) % config.BATCH_SIZE else 0)}回")
    
    # スコアサンプル
    print(f"\n=== スコアサンプル（上位3件） ===")
    scored_articles = [(a, s) for a, s in zip(test_articles, scores)]
    scored_articles.sort(key=lambda x: x[1].total, reverse=True)
    
    for i, (article, score) in enumerate(scored_articles[:3], 1):
        print(f"\n{i}. {article.title[:60]}...")
        print(f"   Total: {score.total}/60 (Tech: {score.tech_score}/30, Culture: {score.culture_score}/30)")
        print(f"   理由: {score.reason[:80]}...")
    
    # Geminiチェック
    print(f"\n=== Gemini残存チェック ===")
    with open(__file__) as f:
        if 'GEMINI' in f.read():
            print("⚠️  警告: テストファイルにGEMINI文字列が残っています")
        else:
            print("✅ OK")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Step 4.2: テスト実行

```bash
cd /Users/rucaye/Documents/Code/rssCallSystem
python test_integrated.py
```

**期待される結果**:

- ✅ エラーなく完了
- ✅ 25記事 → 2バッチ (20+5) で処理
- ✅ 処理時間: 10-15秒
- ✅ "GEMINI" 文字列がログに出ない
- ✅ 全記事でスコア取得成功

---

## 🚀 Phase 4: Reasoning対応プロンプト最適化（別途実施）

### 目的

GPT-5-nanoのReasoning機能を最大限活用し、評価の一貫性・説明可能性・精度を向上させる。

### 実装内容

#### 4.1: プロンプト構造の2段階化

**ファイル**: `src/rules_prompt.txt`

**現在のプロンプト**:

```
あなたは「文化と技術の交差点」専門の記事評価アナリストです。
以下記事を技術面3指標(各0-10点、合計40点相当)と文化面3指標(各0-10点、合計20点相当)で評価。
...
出力は必ず JSON 単体: {"novelty":int, ...}
```

**新プロンプト案**:

```
あなたは「文化と技術の交差点」専門の記事評価アナリストです。

<thinking>
以下の思考プロセスで記事を評価してください:

1. 技術的特徴の抽出
   - この記事が扱う技術は何か？
   - 新規性: 既存技術との差異、革新性
   - 専門性: 技術的深さ、実装詳細度
   - 興味深さ: 学びの価値、応用可能性

2. 文化的要素の分析
   - 文化的関連性: 音楽・アート・写真・健康との接点
   - 生活との接点: 日常生活・季節感・効率化・節約
   - 創造性: デザイン・表現・芸術的貢献

3. 総合評価の根拠
   - 技術面と文化面のバランス
   - 「文化と技術の交差点」としての価値
   - スコアリングの明確な理由付け
</thinking>

<output>
以下のJSON形式で出力してください:
{
  "novelty": 0-10の整数,
  "interest": 0-10の整数,
  "expertise": 0-10の整数,
  "cultural_relevance": 0-10の整数,
  "lifestyle_connection": 0-10の整数,
  "creativity": 0-10の整数,
  "reasoning": "思考過程の要約（技術面・文化面・総合判断を300文字以内で）"
}
</output>

記事:
タイトル: {title}
概要: {summary}
抜粋: {excerpt}
```

#### 4.2: ScoreResultモデル拡張

**ファイル**: `src/models.py`

```diff
  class ScoreResult(BaseModel):
      novelty: int
      interest: int
      expertise: int
      cultural_relevance: int
      lifestyle_connection: int
      creativity: int
-     reason: str
+     reason: str  # 旧フォーマット用（互換性）
+     reasoning: Optional[str] = None  # 新Reasoningフィールド（300文字）
```

#### 4.3: A/Bテスト設計

**テストサンプル**: 20記事（技術10件、文化5件、混合5件）

**測定指標**:

1. **スコア一貫性**: 同じ記事を3回評価してスコアの標準偏差 ≤ 1.5
2. **理由の質**: 人間評価者3名が5段階評価、平均 ≥ 4.0
3. **Reasoning tokens**: 使用量を測定、コスト影響を評価
4. **処理時間**: 旧プロンプトとの比較

**実施期間**: 3-5日

**判定基準**:

- スコア一貫性: ✅ SD ≤ 1.5
- 理由の質: ✅ 平均 ≥ 4.0/5.0
- コスト増: ✅ +20%以内
- 処理時間: ✅ +30%以内

#### 4.4: 段階的ロールアウト

1. **Week 1**: A/Bテスト実施、データ収集
2. **Week 2**: 結果分析、改善必要箇所を特定
3. **Week 3**: 本番環境に適用（フラグで切り替え可能に）
4. **Week 4**: モニタリング、効果測定レポート作成

---

## ⚠️ リスク分析と緩和策

### リスク一覧

| リスク項目 | 発生確率 | 影響度 | 緩和策 |
|-----------|---------|--------|--------|
| レート制限超過 | 低 (20%使用率) | 中 | 指数バックオフ実装済み、エラーハンドリング強化 |
| 単一API依存 | 中 | 高 | Heuristicフォールバック、キャッシュ活用 |
| BATCH_SIZE=20でタイムアウト | 低 | 中 | timeout=120秒設定、max_tokens=8192で余裕確保 |
| 評価精度低下 | 低 | 高 | より多くのコンテキスト送信、Reasoning機能活用 |
| OpenAI API障害 | 低 | 高 | Heuristicフォールバック、ステータス監視 |
| コスト超過 | 低 | 中 | 月額$5上限設定、使用量アラート |

### モニタリング計画

**監視項目**:

1. API呼び出し回数（目標: 5回/100記事）
2. エラー率（目標: <5%）
3. 平均処理時間（目標: <10分/100記事）
4. 月額コスト（目標: <$2）
5. レート制限エラー発生回数（目標: 0回）

**アラート設定**:

- エラー率 > 10%: 即時対応
- 処理時間 > 15分: 調査
- コスト > $3/月: レビュー

---

## 📊 期待される効果

### コスト削減

```
現在 (gpt-4o-mini, BATCH_SIZE=10):
- 100記事 = 10回API呼び出し
- Input: 10 × 10,000 tokens × $0.15/1M = $0.015
- Output: 10 × 2,000 tokens × $0.60/1M = $0.012
- 合計: $0.027/実行

移行後 (gpt-5-nano, BATCH_SIZE=20):
- 100記事 = 5回API呼び出し (-50%)
- Input: 5 × 20,000 tokens × $0.05/1M = $0.005 (-67%)
- Output: 5 × 4,000 tokens × $0.40/1M = $0.008 (-33%)
- 合計: $0.013/実行 (-52%)

月間コスト (30回実行/月):
- 現在: $0.81/月
- 移行後: $0.39/月 (-52%)
```

### 性能向上

1. **評価精度**: 完全な記事コンテキスト（400文字→全文）
2. **処理速度**: バッチサイズ2倍で並列効率向上
3. **Reasoning**: 高度な推論による一貫性向上

### 保守性向上

1. **コード削減**: 約150行削除
2. **複雑性削減**: API選択ロジック削除
3. **テスト簡素化**: 単一API系統

---

## ✅ 完了条件

### Phase 1-3 (本実装)

- [ ] `.cache/scores.jsonl` 削除完了
- [ ] `.env` からGemini設定削除完了
- [ ] `src/config.py` からGemini設定削除完了
- [ ] `src/scorer.py` からGemini関数削除完了（140行）
- [ ] OpenAIインポート無条件化完了
- [ ] `score_article()` OpenAI化完了
- [ ] `score_articles_openai_batch()` 最適化完了
- [ ] API選択ロジック削除完了
- [ ] `test_integrated.py` 作成・実行成功
- [ ] 25記事テストで全記事スコア取得成功
- [ ] ログに"GEMINI"文字列なし確認
- [ ] レート制限エラーなし確認

### Phase 4 (別途実施)

- [ ] 新プロンプト設計完了
- [ ] `ScoreResult` モデル拡張完了
- [ ] A/Bテスト実施完了
- [ ] 測定指標すべて基準クリア
- [ ] 本番環境適用完了
- [ ] 1週間モニタリング完了
- [ ] 効果測定レポート作成完了

---

## 📅 実施スケジュール

### 即時実施（Phase 1-3）

- **所要時間**: 2-3時間
- **実施者**: Development Team
- **リスク**: 低

### 中期実施（Phase 4）

- **開始**: Phase 1-3完了後1週間経過後
- **所要時間**: 2週間
- **実施者**: Development Team + QA
- **リスク**: 中

---

## 📚 参考資料

1. [OpenAI GPT-5-nano Documentation](https://platform.openai.com/docs/models/gpt-5-nano)
2. [OpenAI Rate Limits Guide](https://platform.openai.com/docs/guides/rate-limits)
3. [OpenAI Reasoning Models Guide](https://platform.openai.com/docs/guides/reasoning)
4. [OpenAI Pricing](https://platform.openai.com/docs/pricing)
5. プロジェクト内: `IMPLEMENTATION_REPORT.md`

---

## 承認

**作成**: Development Team  
**レビュー**: _______________  
**承認**: _______________  
**日付**: 2025年12月29日

---

**END OF DOCUMENT**
