from __future__ import annotations
import asyncio
import json
import hashlib
from pathlib import Path
from typing import List
import httpx
import re

from .models import Article, ScoreResult
from . import config
from .logging_utils import get_logger

logger = get_logger(__name__)

CACHE_FILE = Path(config.CACHE_DIR) / "scores.jsonl"

_cache: dict[str, ScoreResult] = {}
if CACHE_FILE.exists():
    try:
        for line in CACHE_FILE.read_text().splitlines():
            obj = json.loads(line)
            _cache[obj["id"]] = ScoreResult(**obj["score"])
    except Exception:
        pass

_cache_lock = asyncio.Lock()

PROMPT_TEMPLATE = """あなたは技術記事評価アナリストです。以下記事を3指標(新規性/興味深さ/専門性)で0-10整数評価し、理由を100文字以内で日本語。
出力は必ず JSON 単体: {{"novelty":int,"interest":int,"expertise":int,"reason":"..."}}.
タイトル: {title}
概要: {summary}
抜粋: {excerpt}
"""

async def score_article(article: Article) -> ScoreResult:
    # cache key
    key = hashlib.sha256(f"{article.title}|{article.url}".encode()).hexdigest()[:16]
    async with _cache_lock:
        if key in _cache:
            return _cache[key]

    # Fallback when no API key (dry run mode)
    if not config.GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not set; using fallback median scores for '%s'", article.title[:30])
        score = ScoreResult(novelty=5, interest=5, expertise=5, reason="fallback:no_api_key")
        async with _cache_lock:
            _cache[key] = score
        return score

    prompt = PROMPT_TEMPLATE.format(title=article.title.replace("'", "\u0027"), summary=article.summary[:300], excerpt=article.excerpt[:300])
    tries = 0
    while True:
        tries += 1
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{config.SCORE_MODEL}:generateContent?key={config.GEMINI_API_KEY}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": config.LLM_TEMPERATURE,
                            "maxOutputTokens": 256,
                        },
                    },
                    headers={"Content-Type": "application/json"},
                )
            if resp.status_code >= 400:
                # 詳細エラーログ（本番は redact 検討）
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
            fenced = re.search(r"```(json)?(.*)```", text, re.DOTALL)
            if fenced:
                text = fenced.group(2).strip()
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                text = json_match.group(0)
            data = json.loads(text)
            novelty = int(data.get("novelty", 5))
            interest = int(data.get("interest", 5))
            expertise = int(data.get("expertise", 5))
            for v in (novelty, interest, expertise):
                if v < 0 or v > 10:
                    raise ValueError("score out of range")
            reason = str(data.get("reason", ""))[:120]
            score = ScoreResult(novelty=novelty, interest=interest, expertise=expertise, reason=reason)
            async with _cache_lock:
                _cache[key] = score
                with CACHE_FILE.open("a") as f:
                    f.write(json.dumps({"id": key, "score": score.model_dump()}, ensure_ascii=False) + "\n")
            return score
        except Exception as e:
            snippet = locals().get("text", "")
            logger.warning(
                "score error (%s) %s: %s %s",
                tries,
                article.title[:30],
                e,
                snippet[:180],
            )
            if tries > config.MAX_SCORE_RETRY:
                score = ScoreResult(novelty=5, interest=5, expertise=5, reason="fallback")
                async with _cache_lock:
                    _cache[key] = score
                return score
            await asyncio.sleep(1 * tries)

async def score_articles(articles: List[Article]) -> List[ScoreResult]:
    sem = asyncio.Semaphore(config.SCORE_CONCURRENCY)
    results: List[ScoreResult] = []
    async def task(a: Article):
        async with sem:
            s = await score_article(a)
            results.append(s)
    await asyncio.gather(*(task(a) for a in articles))
    return results
