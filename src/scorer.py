from __future__ import annotations
import asyncio
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Any, Dict
import httpx
import re
from openai import AsyncOpenAI

from .models import Article, ScoreResult
from . import config
from .logging_utils import get_logger

logger = get_logger(__name__)

CACHE_FILE = Path(config.CACHE_DIR) / "scores.jsonl"
_cache: dict[str, ScoreResult] = {}
_cache_lock = asyncio.Lock()

# Templates  
PROMPT_TEMPLATE = """あなたは「文化と技術の交差点」専門の記事評価アナリストです。以下記事を技術面3指標(各0-10点、合計40点相当)と文化面3指標(各0-10点、合計20点相当)で0-10整数評価。
技術面(重視): novelty(新規性), interest(興味深さ), expertise(専門性)
文化面: cultural_relevance(文化的関連性), lifestyle_connection(生活との接点), creativity(創造性・芸術性)
JSON形式で出力してください。
タイトル: {title}
概要: {summary}
抜粋: {excerpt}
"""

BATCH_PROMPT_TEMPLATE = """あなたは「文化と技術の交差点」専門の記事評価アナリストです。以下の複数記事を技術面3指標(各0-10点、合計40点相当)と文化面3指標(各0-10点、合計20点相当)で0-10整数評価してください。
技術面(重視): novelty(新規性), interest(興味深さ), expertise(専門性)
文化面: cultural_relevance(文化的関連性), lifestyle_connection(生活との接点), creativity(創造性・芸術性)
各記事にid, novelty, interest, expertise, cultural_relevance, lifestyle_connection, creativity, reasonを含むJSON配列形式で出力してください。

記事一覧:
{articles}
"""

# Initialize cache
if CACHE_FILE.exists():
    try:
        for line in CACHE_FILE.read_text().splitlines():
            obj = json.loads(line)
            _cache[obj["id"]] = ScoreResult(**obj["score"])
    except Exception:
        pass

def _generate_heuristic_score(article: Article) -> ScoreResult:
    """Generate heuristic score based on article analysis"""
    title_lower = article.title.lower()
    title_words = len(article.title.split())
    
    # 技術面の評価
    has_code_keywords = any(keyword in title_lower 
                          for keyword in ['api', 'python', 'javascript', 'react', 'ai', 'ml', 'database', 'docker', 'aws'])
    has_advanced_keywords = any(keyword in title_lower 
                              for keyword in ['architecture', 'optimization', 'performance', 'security', 'deployment'])
    
    novelty = 6 if has_advanced_keywords else 5 if has_code_keywords else 4
    interest = min(8, max(4, 4 + title_words // 3))
    expertise = 7 if has_advanced_keywords else 6 if has_code_keywords else 5
    
    # 文化面の評価
    has_cultural_keywords = any(keyword in title_lower 
                               for keyword in ['音楽', 'music', 'アート', 'art', '写真', 'photo', '健康', 'health', 'ウェルネス', 'wellness'])
    has_lifestyle_keywords = any(keyword in title_lower 
                                for keyword in ['生活', 'life', '日常', '季節', 'season', '効率', 'efficiency', '節約'])
    has_creative_keywords = any(keyword in title_lower 
                               for keyword in ['デザイン', 'design', 'クリエイティブ', 'creative', '表現'])
    
    cultural_relevance = 6 if has_cultural_keywords else 5
    lifestyle_connection = 6 if has_lifestyle_keywords else 5
    creativity = 6 if has_creative_keywords else 5
    
    return ScoreResult(
        novelty=novelty, interest=interest, expertise=expertise,
        cultural_relevance=cultural_relevance, lifestyle_connection=lifestyle_connection, creativity=creativity,
        reason="fallback:heuristic_analysis"
    )

def _extract_json_from_text(text: str) -> Any:
    """Extract and parse JSON from API response text"""
    # Remove code blocks
    fenced = re.search(r"```(json)?(.*)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(2).strip()
    
    # Extract JSON object or array
    json_match = re.search(r"[\[\{].*[\]\}]", text, re.DOTALL)
    if json_match:
        text = json_match.group(0)
    
    return json.loads(text)

def _validate_score(score: int) -> bool:
    """Validate if score is in valid range"""
    return 0 <= score <= 10

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

    # Call OpenAI API with retry logic
    tries = 0
    score = None
    
    while tries < config.MAX_SCORE_RETRY:
        tries += 1
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
                    {"role": "system", "content": "あなたは技術記事評価の専門家です。与えられた記事を客観的に評価してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=1024,
                reasoning_effort="minimal",  # minimal reasoning for cost/performance on this simple scoring task
                response_format={"type": "json_object"},
                timeout=30.0
            )
            
            text = response.choices[0].message.content.strip()
            data = json.loads(text)
            
            # Validate and create score
            scores = {
                "novelty": int(data.get("novelty", 5)),
                "interest": int(data.get("interest", 5)),
                "expertise": int(data.get("expertise", 5)),
                "cultural_relevance": int(data.get("cultural_relevance", 5)),
                "lifestyle_connection": int(data.get("lifestyle_connection", 5)),
                "creativity": int(data.get("creativity", 5))
            }
            
            if all(_validate_score(s) for s in scores.values()):
                score = ScoreResult(
                    **scores,
                    reason=str(data.get("reason", ""))[:120]
                )
                break
            else:
                logger.warning("Invalid scores for article '%s'", article.title[:30])
                raise ValueError("Invalid score range")
                
        except Exception as e:
            logger.warning("OpenAI API error (attempt %d/%d) for '%s': %s", 
                          tries, config.MAX_SCORE_RETRY, article.title[:30], str(e)[:100])
            
            if tries >= config.MAX_SCORE_RETRY:
                break
                
            # Exponential backoff
            delay = (2 ** (tries - 1)) + (0.1 * tries)
            if "429" in str(e) or "rate_limit" in str(e).lower():
                delay *= 2
                logger.info("Rate limit detected, backing off for %.1f seconds", delay)
            await asyncio.sleep(delay)
    
    # Use heuristic fallback if all retries failed
    if not score:
        logger.warning("All retry attempts failed for '%s', using heuristic", article.title[:30])
        score = _generate_heuristic_score(article)
    
    # Cache result
    async with _cache_lock:
        _cache[key] = score
        with CACHE_FILE.open("a") as f:
            f.write(json.dumps({"id": key, "score": score.model_dump()}, ensure_ascii=False) + "\n")
    
    return score


async def score_articles_openai_batch(articles: List[Article], batch_id: int = 0) -> List[ScoreResult]:
    """Score multiple articles using OpenAI GPT-5-nano API in batch"""
    if not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; using fallback for batch %d (%d articles)", batch_id, len(articles))
        return [ScoreResult(
            novelty=5, interest=5, expertise=5,
            cultural_relevance=5, lifestyle_connection=5, creativity=5,
            reason="fallback:no_openai_key"
        ) for _ in articles]
    
    client = AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        organization=config.OPENAI_ORGANIZATION or None
    )
    
    # Build batch prompt (with full article content for better evaluation)
    articles_text = ""
    for i, article in enumerate(articles):
        articles_text += f"記事ID: {i}\n"
        articles_text += f"タイトル: {article.title}\n"
        articles_text += f"概要: {article.summary[:400]}\n"
        articles_text += f"抜粋: {article.excerpt}\n\n"
    
    prompt = BATCH_PROMPT_TEMPLATE.format(articles=articles_text)
    
    # Try API call with retry
    tries = 0
    while tries < config.MAX_SCORE_RETRY:
        tries += 1
        try:
            response = await client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "あなたは技術記事評価の専門家です。与えられた記事を客観的に評価してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=16384,
                # Use minimal reasoning for batch classification to control cost/latency
                reasoning_effort="minimal",
                response_format={"type": "json_object"},
                timeout=120.0
            )
            
            text = response.choices[0].message.content.strip()
            data = json.loads(text)
            
            # Handle nested JSON structure
            if "articles" in data:
                data = data["articles"]
            elif not isinstance(data, list):
                # Try to find the first list value
                for value in data.values():
                    if isinstance(value, list):
                        data = value
                        break
                else:
                    raise ValueError("No list found in response")
            
            # Process results
            results = []
            for i, article in enumerate(articles):
                article_result = next((item for item in data if item.get("id") == i), None)
                
                if article_result:
                    try:
                        novelty = int(article_result.get("novelty", 5))
                        interest = int(article_result.get("interest", 5))
                        expertise = int(article_result.get("expertise", 5))
                        cultural_relevance = int(article_result.get("cultural_relevance", 5))
                        lifestyle_connection = int(article_result.get("lifestyle_connection", 5))
                        creativity = int(article_result.get("creativity", 5))
                        reason = str(article_result.get("reason", ""))[:120]
                        
                        if all(_validate_score(s) for s in [novelty, interest, expertise, cultural_relevance, lifestyle_connection, creativity]):
                            results.append(ScoreResult(
                                novelty=novelty, interest=interest, expertise=expertise,
                                cultural_relevance=cultural_relevance, lifestyle_connection=lifestyle_connection, creativity=creativity,
                                reason=reason
                            ))
                        else:
                            results.append(_generate_heuristic_score(article))
                    except (ValueError, TypeError):
                        results.append(_generate_heuristic_score(article))
                else:
                    results.append(ScoreResult(
                        novelty=5, interest=5, expertise=5,
                        cultural_relevance=5, lifestyle_connection=5, creativity=5,
                        reason="fallback:not_in_openai_response"
                    ))
            
            logger.info("OpenAI batch %d completed successfully: %d articles scored", batch_id, len(results))
            return results
            
        except Exception as e:
            logger.warning("OpenAI batch score error (%s) batch %d: %s", tries, batch_id, str(e)[:180])
            
            if tries >= config.MAX_SCORE_RETRY:
                break
                
            # Exponential backoff
            delay = (2 ** (tries - 1)) + (0.1 * tries)
            if "429" in str(e) or "rate_limit" in str(e).lower():
                delay *= 2
            await asyncio.sleep(delay)
    
    # Fallback to heuristic scoring
    logger.info("OpenAI batch %d failed, using heuristic fallback for %d articles", batch_id, len(articles))
    return [_generate_heuristic_score(article) for article in articles]


async def score_articles(articles: List[Article]) -> List[ScoreResult]:
    """Score articles using either batch processing or individual scoring"""
    if config.USE_BATCH_SCORING and len(articles) > 5:
        return await _process_batch_scoring(articles)
    else:
        return await _process_individual_scoring(articles)

async def _process_batch_scoring(articles: List[Article]) -> List[ScoreResult]:
    """Process articles using OpenAI batch scoring"""
    logger.info("Using OpenAI batch scoring for %d articles (batch size: %d)", 
               len(articles), config.BATCH_SIZE)
    
    all_results: List[ScoreResult] = []
    
    for i in range(0, len(articles), config.BATCH_SIZE):
        batch = articles[i:i + config.BATCH_SIZE]
        batch_id = i // config.BATCH_SIZE + 1
        
        logger.info("Processing batch %d: articles %d-%d", batch_id, i+1, i+len(batch))
        
        try:
            # Process batch with OpenAI
            batch_results = await score_articles_openai_batch(batch, batch_id)
                
            all_results.extend(batch_results)
            await _cache_batch_results(batch, batch_results)
            
            # Small delay between batches
            if i + config.BATCH_SIZE < len(articles):
                await asyncio.sleep(1.0)
                
        except Exception as e:
            logger.error("Batch processing failed for batch %d: %s", batch_id, e)
            # Fallback to individual scoring
            fallback_results = await _fallback_individual_scoring(batch)
            all_results.extend(fallback_results)
    
    return all_results

async def _process_individual_scoring(articles: List[Article]) -> List[ScoreResult]:
    """Process articles using individual scoring"""
    logger.info("Using individual scoring for %d articles", len(articles))
    sem = asyncio.Semaphore(config.SCORE_CONCURRENCY)
    
    async def task(article: Article):
        async with sem:
            return await score_article(article)
    
    return await asyncio.gather(*(task(a) for a in articles))

async def _cache_batch_results(batch: List[Article], results: List[ScoreResult]):
    """Cache batch results"""
    async with _cache_lock:
        for article, result in zip(batch, results):
            key = hashlib.sha256(f"{article.title}|{article.url}".encode()).hexdigest()[:16]
            if key not in _cache:  # Only cache new results
                _cache[key] = result
                with CACHE_FILE.open("a") as f:
                    f.write(json.dumps({"id": key, "score": result.model_dump()}, ensure_ascii=False) + "\n")

async def _fallback_individual_scoring(batch: List[Article]) -> List[ScoreResult]:
    """Fallback to individual scoring for a batch"""
    logger.info("Falling back to individual scoring for %d articles", len(batch))
    sem = asyncio.Semaphore(1)  # Very conservative for fallback
    
    async def individual_task(article: Article):
        async with sem:
            return await score_article(article)
    
    return await asyncio.gather(*(individual_task(a) for a in batch))
