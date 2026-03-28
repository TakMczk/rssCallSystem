import type { FeedArticle, FeedPayload } from './types'

export type SortMode = 'recommended' | 'score' | 'latest'
export type CategoryMode = 'all' | 'tech' | 'culture'

const SOURCE_LABELS: Record<string, string> = {
  'zenn.dev': 'Zenn',
  'qiita.com': 'Qiita',
  'codezine.jp': 'CodeZine',
  'publickey1.jp': 'Publickey',
  'hnrss.org': 'Hacker News',
  'lobste.rs': 'Lobsters',
  'arstechnica.com': 'Ars Technica',
  'theverge.com': 'The Verge',
  'technologyreview.jp': 'MIT Technology Review',
  'japan.zdnet.com': 'ZDNet Japan',
  'wirelesswire.jp': 'WirelessWire',
  'wired.jp': 'WIRED Japan',
  'xenospectrum.com': 'XenoSpectrum',
  'nikkeibp.co.jp': '日経クロステック',
  'b.hatena.ne.jp': 'はてなブックマーク',
}

export function getHostname(source: string): string {
  try {
    return new URL(source).hostname.replace(/^www\./, '')
  } catch {
    return source
  }
}

export function getSourceLabel(source: string): string {
  const hostname = getHostname(source)
  return SOURCE_LABELS[hostname] ?? hostname
}

export function formatDate(value: string | null): string {
  if (!value) {
    return '未設定'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '不明'
  }
  return new Intl.DateTimeFormat('ja-JP', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function getSummary(article: FeedArticle): string {
  return article.summaryJa?.trim() || article.excerpt || '要約はまだありません。'
}

export function getDisplayTitle(article: FeedArticle): string {
  return article.titleJa?.trim() || article.title
}

function compareByLatest(a: FeedArticle, b: FeedArticle): number {
  const aDate = new Date(a.freshnessAt ?? a.publishedAt).getTime()
  const bDate = new Date(b.freshnessAt ?? b.publishedAt).getTime()
  return bDate - aDate
}

export function sortArticles(
  articles: FeedArticle[],
  sortMode: SortMode,
  categoryMode: CategoryMode,
): FeedArticle[] {
  const next = [...articles]

  next.sort((a, b) => {
    if (sortMode === 'latest') {
      return compareByLatest(a, b) || a.rank - b.rank
    }
    if (sortMode === 'score') {
      return b.scores.total - a.scores.total || a.rank - b.rank
    }
    if (categoryMode === 'tech') {
      return b.techScore - a.techScore || b.scores.total - a.scores.total || a.rank - b.rank
    }
    if (categoryMode === 'culture') {
      return (
        b.cultureScore - a.cultureScore ||
        b.scores.total - a.scores.total ||
        a.rank - b.rank
      )
    }
    return a.rank - b.rank
  })

  return next
}

export function isFeedPayload(value: unknown): value is FeedPayload {
  if (!value || typeof value !== 'object') {
    return false
  }
  const payload = value as Partial<FeedPayload>
  return (
    typeof payload.schemaVersion === 'string' &&
    typeof payload.generatedAt === 'string' &&
    Array.isArray(payload.articles)
  )
}

function stripRankSuffix(title: string): string {
  return title.replace(/\s*\[#\d+\s+Score:\d+\]$/, '').trim()
}

export function parseLegacyRssFeed(xmlText: string): FeedPayload {
  const parser = new DOMParser()
  const xml = parser.parseFromString(xmlText, 'application/xml')
  const parserError = xml.querySelector('parsererror')
  if (parserError) {
    throw new Error('rss.xml を解析できませんでした')
  }

  const items = Array.from(xml.querySelectorAll('item'))
  const lastBuildDate = xml.querySelector('lastBuildDate')?.textContent?.trim()
  const articles = items.map((item, index) => {
    const descriptionHtml = item.querySelector('description')?.textContent ?? ''
    const descriptionDoc = parser.parseFromString(descriptionHtml, 'text/html')
    const paragraphs = Array.from(descriptionDoc.querySelectorAll('p'))
      .map((element) => element.textContent?.trim() ?? '')
      .filter(Boolean)
    const scoreMatch = descriptionHtml.match(
      /Score:\s*(\d+).*?N=(\d+)\/I=(\d+)\/E=(\d+).*?C=(\d+)\/L=(\d+)\/Cr=(\d+)/s,
    )
    const reason =
      paragraphs.find((text) => text.startsWith('Reason:'))?.replace(/^Reason:\s*/, '') ?? ''
    const excerpt =
      paragraphs.find((text) => text.startsWith('Excerpt:'))?.replace(/^Excerpt:\s*/, '') ??
      paragraphs[0] ??
      ''
    const originalUrl =
      paragraphs
        .find((text) => text.startsWith('Original URL:'))
        ?.replace(/^Original URL:\s*/, '') ??
      item.querySelector('link')?.textContent?.trim() ??
      ''
    const source =
      originalUrl && /^https?:\/\//.test(originalUrl)
        ? `${new URL(originalUrl).origin}/`
        : item.querySelector('link')?.textContent?.trim() ?? ''

    const novelty = Number(scoreMatch?.[2] ?? 0)
    const interest = Number(scoreMatch?.[3] ?? 0)
    const expertise = Number(scoreMatch?.[4] ?? 0)
    const culturalRelevance = Number(scoreMatch?.[5] ?? 0)
    const lifestyleConnection = Number(scoreMatch?.[6] ?? 0)
    const creativity = Number(scoreMatch?.[7] ?? 0)

    return {
      rank: index + 1,
      id:
        item.querySelector('guid')?.textContent?.trim() ??
        item.querySelector('link')?.textContent?.trim() ??
        `rss-${index + 1}`,
      title: stripRankSuffix(item.querySelector('title')?.textContent?.trim() ?? 'Untitled'),
      titleJa: null,
      url: originalUrl,
      source,
      publishedAt: item.querySelector('pubDate')?.textContent?.trim() ?? new Date().toISOString(),
      freshnessAt: item.querySelector('pubDate')?.textContent?.trim() ?? null,
      summaryJa: paragraphs[0] ?? null,
      excerpt,
      reason,
      techScore: novelty + interest + expertise,
      cultureScore: culturalRelevance + lifestyleConnection + creativity,
      scores: {
        total: Number(scoreMatch?.[1] ?? 0),
        novelty,
        interest,
        expertise,
        culturalRelevance,
        lifestyleConnection,
        creativity,
      },
    }
  })

  return {
    schemaVersion: 'rss-compat',
    generatedAt: lastBuildDate ? new Date(lastBuildDate).toISOString() : new Date().toISOString(),
    articles,
  }
}
