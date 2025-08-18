from __future__ import annotations
import asyncio
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Any, Dict
import httpx
import re

from models import Article, ScoreResult
import config
from logging_utils import get_logger

logger = get_logger(__name__)

# OpenAI client will be imported conditionally
try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    logger.warning("OpenAI library not installed")
    HAS_OPENAI = False

CACHE_FILE = Path(config.CACHE_DIR) / "scores.jsonl"
_cache: dict[str, ScoreResult] = {}
_cache_lock = asyncio.Lock()

# Templates
PROMPT_TEMPLATE = """あなたは技術記事評価アナリストです。以下記事を3指標(新規性/興味深さ/専門性)で0-10整数評価し、理由を100文字以内で日本語。
出力は必ず JSON 単体: {{"novelty":int,"interest":int,"expertise":int,"reason":"..."}}.
タイトル: {title}
概要: {summary}
抜粋: {excerpt}
"""

BATCH_PROMPT_TEMPLATE = """あなたは技術記事評価アナリストです。以下の複数の技術記事を3指標(新規性/興味深さ/専門性)で0-10整数評価してください。
出力は必ずJSON配列形式: [{{"id":int,"novelty":int,"interest":int,"expertise":int,"reason":"理由(100文字以内)"}}, ...]

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
    title_words = len(article.title.split())
    has_code_keywords = any(keyword in article.title.lower() 
                          for keyword in ['api', 'python', 'javascript', 'react', 'ai', 'ml', 'database', 'docker', 'aws'])
    has_advanced_keywords = any(keyword in article.title.lower() 
                              for keyword in ['architecture', 'optimization', 'performance', 'security', 'deployment'])
    
    novelty = 6 if has_advanced_keywords else 5 if has_code_keywords else 4
    interest = min(8, max(4, 4 + title_words // 3))
    expertise = 7 if has_advanced_keywords else 6 if has_code_keywords else 5
    
    return ScoreResult(novelty=novelty, interest=interest, expertise=expertise, reason="fallback:heuristic_analysis")

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
    """Score a single article"""
    # Check cache
    key = hashlib.sha256(f"{article.title}|{article.url}".encode()).hexdigest()[:16]
    async with _cache_lock:
        if key in _cache:
            return _cache[key]

    # Fallback if no API key
    if not config.GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not set; using fallback for '%s'", article.title[:30])
        score = ScoreResult(novelty=5, interest=5, expertise=5, reason="fallback:no_api_key")
        async with _cache_lock:
            _cache[key] = score
        return score

    # Try scoring with API
    prompt = PROMPT_TEMPLATE.format(
        title=article.title.replace("'", "\u0027"), 
        summary=article.summary[:300], 
        excerpt=article.excerpt[:300]
    )
    
    score = await _score_with_retry(prompt, article.title, key, is_batch=False)
    if not score:
        score = _generate_heuristic_score(article)
        
    async with _cache_lock:
        _cache[key] = score
        if key not in _cache:  # Only write to file if not already cached
            with CACHE_FILE.open("a") as f:
                f.write(json.dumps({"id": key, "score": score.model_dump()}, ensure_ascii=False) + "\n")
    
    return score

async def _score_with_retry(prompt: str, context: str, cache_key: str, is_batch: bool = False) -> Optional[ScoreResult]:
    """Generic retry logic for API scoring"""
    tries = 0
    base_delay = 1
    max_tokens = 2048 if is_batch else 256
    timeout = 60 if is_batch else 30
    
    while tries < config.MAX_SCORE_RETRY:
        tries += 1
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{config.SCORE_MODEL}:generateContent?key={config.GEMINI_API_KEY}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": config.LLM_TEMPERATURE,
                            "maxOutputTokens": max_tokens,
                        },
                    },
                    headers={"Content-Type": "application/json"},
                )
            
            if resp.status_code >= 400:
                logger.error("Gemini API error %s: %s", resp.status_code, resp.text[:500])
                resp.raise_for_status()
                
            body = resp.json()
            candidates = body.get("candidates", [])
            if not candidates:
                raise ValueError("no candidates")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("no parts")
            text = "\n".join(p.get("text", "") for p in parts).strip()
            
            data = _extract_json_from_text(text)
            
            if is_batch:
                return data  # Return raw data for batch processing
            else:
                # Single article processing
                novelty = int(data.get("novelty", 5))
                interest = int(data.get("interest", 5))
                expertise = int(data.get("expertise", 5))
                
                if not all(_validate_score(s) for s in [novelty, interest, expertise]):
                    raise ValueError("score out of range")
                    
                reason = str(data.get("reason", ""))[:120]
                return ScoreResult(novelty=novelty, interest=interest, expertise=expertise, reason=reason)
                
        except Exception as e:
            logger.warning("Score error (%s) %s: %s", tries, context[:30], str(e)[:180])
            
            if tries >= config.MAX_SCORE_RETRY:
                return None
                
            # Exponential backoff
            delay = base_delay * (2 ** (tries - 1)) + (0.1 * tries)
            if "429" in str(e) or "Too Many Requests" in str(e):
                delay *= 2
            await asyncio.sleep(delay)
    
    return None

async def score_articles_batch(articles: List[Article], batch_id: int = 0) -> List[ScoreResult]:
    """Score multiple articles in a single Gemini API call"""
    if not config.GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not set; using fallback for batch %d (%d articles)", batch_id, len(articles))
        return [ScoreResult(novelty=5, interest=5, expertise=5, reason="fallback:no_api_key") for _ in articles]
    
    # Build batch prompt
    articles_text = ""
    for i, article in enumerate(articles):
        articles_text += f"記事ID: {i}\n"
        articles_text += f"タイトル: {article.title[:100]}\n"
        articles_text += f"概要: {article.summary[:200]}\n"
        articles_text += f"抜粋: {article.excerpt[:200]}\n\n"
    
    prompt = BATCH_PROMPT_TEMPLATE.format(articles=articles_text)
    
    # Try API call with retry
    data = await _score_with_retry(prompt, f"batch {batch_id}", "", is_batch=True)
    
    if not data or not isinstance(data, list):
        # Fallback to heuristic scoring
        logger.info("Batch %d failed, using heuristic fallback for %d articles", batch_id, len(articles))
        return [_generate_heuristic_score(article) for article in articles]
    
    # Process batch response
    results = []
    for i, article in enumerate(articles):
        article_result = next((item for item in data if item.get("id") == i), None)
        
        if article_result:
            try:
                novelty = int(article_result.get("novelty", 5))
                interest = int(article_result.get("interest", 5))
                expertise = int(article_result.get("expertise", 5))
                reason = str(article_result.get("reason", ""))[:120]
                
                if all(_validate_score(s) for s in [novelty, interest, expertise]):
                    results.append(ScoreResult(novelty=novelty, interest=interest, expertise=expertise, reason=reason))
                else:
                    results.append(_generate_heuristic_score(article))
            except (ValueError, TypeError):
                results.append(_generate_heuristic_score(article))
        else:
            results.append(ScoreResult(novelty=5, interest=5, expertise=5, reason="fallback:not_in_batch_response"))
    
    logger.info("Batch %d completed successfully: %d articles scored", batch_id, len(results))
    return results


async def score_articles_openai_batch(articles: List[Article], batch_id: int = 0) -> List[ScoreResult]:
    """Score multiple articles using OpenAI GPT API in batch"""
    if not HAS_OPENAI or not config.OPENAI_API_KEY:
        reason = "fallback:no_openai_library" if not HAS_OPENAI else "fallback:no_openai_key"
        logger.info("OpenAI unavailable; using fallback for batch %d (%d articles)", batch_id, len(articles))
        return [ScoreResult(novelty=5, interest=5, expertise=5, reason=reason) for _ in articles]
    
    client = AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        organization=config.OPENAI_ORGANIZATION or None
    )
    
    # Build batch prompt
    articles_text = ""
    for i, article in enumerate(articles):
        articles_text += f"記事ID: {i}\n"
        articles_text += f"タイトル: {article.title[:100]}\n"
        articles_text += f"概要: {article.summary[:200]}\n"
        articles_text += f"抜粋: {article.excerpt[:200]}\n\n"
    
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
                temperature=config.LLM_TEMPERATURE,
                max_tokens=2048,
                response_format={"type": "json_object"}
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
                        reason = str(article_result.get("reason", ""))[:120]
                        
                        if all(_validate_score(s) for s in [novelty, interest, expertise]):
                            results.append(ScoreResult(novelty=novelty, interest=interest, expertise=expertise, reason=reason))
                        else:
                            results.append(_generate_heuristic_score(article))
                    except (ValueError, TypeError):
                        results.append(_generate_heuristic_score(article))
                else:
                    results.append(ScoreResult(novelty=5, interest=5, expertise=5, reason="fallback:not_in_openai_response"))
            
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
    """Process articles using batch scoring"""
    api_method = "OpenAI" if config.USE_OPENAI else "Gemini"
    logger.info("Using %s batch scoring for %d articles (batch size: %d)", 
               api_method, len(articles), config.BATCH_SIZE)
    
    all_results: List[ScoreResult] = []
    
    for i in range(0, len(articles), config.BATCH_SIZE):
        batch = articles[i:i + config.BATCH_SIZE]
        batch_id = i // config.BATCH_SIZE + 1
        
        logger.info("Processing batch %d: articles %d-%d", batch_id, i+1, i+len(batch))
        
        try:
            # Choose batch processing method
            if config.USE_OPENAI:
                batch_results = await score_articles_openai_batch(batch, batch_id)
            else:
                batch_results = await score_articles_batch(batch, batch_id)
                
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
