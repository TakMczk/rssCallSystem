export type ArticleScores = {
  total: number
  novelty: number
  interest: number
  expertise: number
  culturalRelevance: number
  lifestyleConnection: number
  creativity: number
}

export type FeedArticle = {
  rank: number
  id: string
  title: string
  titleJa?: string | null
  url: string
  source: string
  publishedAt: string
  freshnessAt: string | null
  summaryJa: string | null
  excerpt: string
  reason: string
  techScore: number
  cultureScore: number
  scores: ArticleScores
}

export type FeedPayload = {
  schemaVersion: string
  generatedAt: string
  articles: FeedArticle[]
}

export type HistoryIndexPayload = {
  schemaVersion: string
  latestDate: string | null
  availableDates: string[]
}
