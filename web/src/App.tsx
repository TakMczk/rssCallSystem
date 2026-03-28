import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  CssBaseline,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  LinearProgress,
  Link,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  ThemeProvider,
  Toolbar,
  Tooltip,
  Typography,
  createTheme,
} from '@mui/material'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'
import RssFeedIcon from '@mui/icons-material/RssFeed'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import PublicIcon from '@mui/icons-material/Public'
import UpdateIcon from '@mui/icons-material/Update'
import InsightsIcon from '@mui/icons-material/Insights'
import type { FeedArticle, FeedPayload } from './types'

type SortMode = 'recommended' | 'score' | 'latest'
type CategoryMode = 'all' | 'tech' | 'culture'
type ThemeMode = 'light' | 'dark'
type DataOrigin = 'json' | 'rss-fallback'

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

const scoreLabels = [
  { key: 'novelty', label: '新規性' },
  { key: 'interest', label: '興味性' },
  { key: 'expertise', label: '専門性' },
  { key: 'culturalRelevance', label: '文化関連性' },
  { key: 'lifestyleConnection', label: '生活接続性' },
  { key: 'creativity', label: '創造性' },
] as const

function getHostname(source: string): string {
  try {
    return new URL(source).hostname.replace(/^www\./, '')
  } catch {
    return source
  }
}

function getSourceLabel(source: string): string {
  const hostname = getHostname(source)
  return SOURCE_LABELS[hostname] ?? hostname
}

function formatDate(value: string | null): string {
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

function getSummary(article: FeedArticle): string {
  return article.summaryJa?.trim() || article.excerpt || '要約はまだありません。'
}

function compareByLatest(a: FeedArticle, b: FeedArticle): number {
  const aDate = new Date(a.freshnessAt ?? a.publishedAt).getTime()
  const bDate = new Date(b.freshnessAt ?? b.publishedAt).getTime()
  return bDate - aDate
}

function sortArticles(
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

function isFeedPayload(value: unknown): value is FeedPayload {
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

function parseLegacyRssFeed(xmlText: string): FeedPayload {
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
    const reason = paragraphs.find((text) => text.startsWith('Reason:'))?.replace(/^Reason:\s*/, '') ?? ''
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

function createAppTheme(mode: ThemeMode) {
  return createTheme({
    palette: {
      mode,
      primary: {
        main: mode === 'dark' ? '#90caf9' : '#1565c0',
      },
      secondary: {
        main: mode === 'dark' ? '#f48fb1' : '#7b1fa2',
      },
      background: {
        default: mode === 'dark' ? '#0f172a' : '#f4f7fb',
        paper: mode === 'dark' ? '#111827' : '#ffffff',
      },
    },
    shape: {
      borderRadius: 16,
    },
    typography: {
      fontFamily:
        '"Inter", "Noto Sans JP", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      h3: {
        fontWeight: 700,
      },
      h4: {
        fontWeight: 700,
      },
      h6: {
        fontWeight: 700,
      },
    },
  })
}

function App() {
  const [payload, setPayload] = useState<FeedPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dataOrigin, setDataOrigin] = useState<DataOrigin | null>(null)
  const [themeMode, setThemeMode] = useState<ThemeMode>('light')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [sortMode, setSortMode] = useState<SortMode>('recommended')
  const [categoryMode, setCategoryMode] = useState<CategoryMode>('all')

  useEffect(() => {
    const storedMode = window.localStorage.getItem('rss-call-theme')
    if (storedMode === 'light' || storedMode === 'dark') {
      setThemeMode(storedMode)
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setThemeMode('dark')
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem('rss-call-theme', themeMode)
  }, [themeMode])

  useEffect(() => {
    let active = true

    async function load() {
      try {
        setLoading(true)
        setError(null)
        const response = await fetch('./data.json', { cache: 'no-store' })
        if (response.ok) {
          const data: unknown = await response.json()
          if (!isFeedPayload(data)) {
            throw new Error('data.json の形式が想定と異なります')
          }
          if (active) {
            setPayload(data)
            setDataOrigin('json')
          }
          return
        }

        const rssResponse = await fetch('./rss.xml', { cache: 'no-store' })
        if (!rssResponse.ok) {
          throw new Error(
            `data.json (${response.status}) と rss.xml (${rssResponse.status}) の取得に失敗しました`,
          )
        }
        const rssText = await rssResponse.text()
        const rssPayload = parseLegacyRssFeed(rssText)
        if (active) {
          setPayload(rssPayload)
          setDataOrigin('rss-fallback')
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : '不明なエラーが発生しました')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [])

  const theme = useMemo(() => createAppTheme(themeMode), [themeMode])
  const sourceOptions = useMemo(() => {
    const labels = new Map<string, string>()
    payload?.articles.forEach((article) => {
      labels.set(article.source, getSourceLabel(article.source))
    })
    return Array.from(labels.entries()).sort((a, b) => a[1].localeCompare(b[1], 'ja'))
  }, [payload])

  const filteredArticles = useMemo(() => {
    const articles = payload?.articles ?? []
    const narrowed =
      sourceFilter === 'all'
        ? articles
        : articles.filter((article) => article.source === sourceFilter)
    return sortArticles(narrowed, sortMode, categoryMode)
  }, [categoryMode, payload, sortMode, sourceFilter])

  const topArticle = filteredArticles[0] ?? null

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <AppBar position="sticky" color="transparent" elevation={0} sx={{ backdropFilter: 'blur(12px)' }}>
          <Toolbar sx={{ gap: 2 }}>
            <Stack spacing={0.25} sx={{ flexGrow: 1 }}>
              <Typography variant="h6">Tech Curated Feed</Typography>
              <Typography variant="body2" color="text.secondary">
                AI が評価した技術記事を、要約とスコアつきで見やすく一覧化
              </Typography>
            </Stack>
            <Tooltip title={themeMode === 'dark' ? 'ライトモード' : 'ダークモード'}>
              <IconButton
                color="primary"
                onClick={() => setThemeMode((prev) => (prev === 'dark' ? 'light' : 'dark'))}
              >
                {themeMode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
              </IconButton>
            </Tooltip>
            <Button
              component="a"
              href="./rss.xml"
              target="_blank"
              rel="noreferrer"
              startIcon={<RssFeedIcon />}
              variant="contained"
            >
              RSS を購読
            </Button>
          </Toolbar>
        </AppBar>

        <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
          <Stack spacing={3}>
            <Card sx={{ overflow: 'hidden' }}>
              <Box
                sx={{
                  px: { xs: 3, md: 4 },
                  py: { xs: 3, md: 4 },
                  background:
                    themeMode === 'dark'
                      ? 'linear-gradient(135deg, rgba(21,101,192,0.24), rgba(123,31,162,0.18))'
                      : 'linear-gradient(135deg, rgba(21,101,192,0.08), rgba(123,31,162,0.08))',
                }}
              >
                <Stack spacing={2}>
                  <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} justifyContent="space-between">
                    <Box>
                      <Typography variant="h3" gutterBottom>
                        技術記事を、読む前にわかりやすく
                      </Typography>
                      <Typography variant="body1" color="text.secondary">
                        記事ごとの日本語要約、Tech / Culture のスコア、評価理由をまとめて確認できます。
                        英語記事も通常経路では日本語要約で把握できます。
                      </Typography>
                    </Box>
                    <Stack direction="row" spacing={1} alignItems="flex-start" flexWrap="wrap" useFlexGap>
                      <Chip icon={<PublicIcon />} label={`記事数 ${payload?.articles.length ?? 0}`} color="primary" />
                      <Chip icon={<UpdateIcon />} label={`最終更新 ${payload ? formatDate(payload.generatedAt) : '取得中'}`} />
                      <Chip icon={<InsightsIcon />} label="評価軸 6 項目" variant="outlined" />
                    </Stack>
                  </Stack>

                  <Grid container spacing={2}>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle1" gutterBottom>
                            収集元
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Qiita / Zenn / CodeZine に加え、Hacker News、Lobsters、Ars Technica、
                            The Verge など海外ソースも巡回します。
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle1" gutterBottom>
                            表示内容
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            タイトルだけでなく、評価理由・スコア内訳・要約をカード形式で表示します。
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid size={{ xs: 12, md: 4 }}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle1" gutterBottom>
                            システム状態
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            RSS 生成と GitHub Pages 配信を継続しつつ、`data.json` を使って静的サイトとして公開します。
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Stack>
              </Box>
            </Card>

            <Card>
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="h6">絞り込みと並び替え</Typography>
                  <Stack
                    direction={{ xs: 'column', md: 'row' }}
                    spacing={2}
                    alignItems={{ xs: 'stretch', md: 'center' }}
                  >
                    <FormControl size="small" sx={{ minWidth: 220 }}>
                      <InputLabel id="source-filter-label">ソース</InputLabel>
                      <Select
                        labelId="source-filter-label"
                        label="ソース"
                        value={sourceFilter}
                        onChange={(event) => setSourceFilter(event.target.value)}
                      >
                        <MenuItem value="all">すべてのソース</MenuItem>
                        {sourceOptions.map(([value, label]) => (
                          <MenuItem key={value} value={value}>
                            {label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 180 }}>
                      <InputLabel id="sort-mode-label">並び順</InputLabel>
                      <Select
                        labelId="sort-mode-label"
                        label="並び順"
                        value={sortMode}
                        onChange={(event) => setSortMode(event.target.value as SortMode)}
                      >
                        <MenuItem value="recommended">おすすめ順</MenuItem>
                        <MenuItem value="score">総合スコア順</MenuItem>
                        <MenuItem value="latest">新着順</MenuItem>
                      </Select>
                    </FormControl>

                    <Tabs
                      value={categoryMode}
                      onChange={(_event, value: CategoryMode) => setCategoryMode(value)}
                      sx={{ minHeight: 40 }}
                    >
                      <Tab value="all" label="All" />
                      <Tab value="tech" label="Tech" />
                      <Tab value="culture" label="Culture" />
                    </Tabs>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>

            {loading ? (
              <Card>
                <CardContent>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <CircularProgress size={28} />
                    <Typography>記事データを読み込んでいます…</Typography>
                  </Stack>
                </CardContent>
              </Card>
            ) : null}

            {error ? <Alert severity="error">{error}</Alert> : null}

            {!loading && !error && dataOrigin === 'rss-fallback' ? (
              <Alert severity="info">
                `data.json` が未生成のため、現在は `rss.xml` から互換表示しています。次回パイプライン実行後は要約や鮮度情報も
                `data.json` から読み込みます。
              </Alert>
            ) : null}

            {!loading && !error && topArticle ? (
              <Card sx={{ border: 1, borderColor: 'primary.main' }}>
                <CardContent>
                  <Stack spacing={1.5}>
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} justifyContent="space-between">
                      <Box>
                        <Typography variant="overline" color="primary.main">
                          Pick of the feed
                        </Typography>
                        <Typography variant="h5">{topArticle.title}</Typography>
                      </Box>
                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        <Chip label={`Rank #${topArticle.rank}`} color="primary" />
                        <Chip label={`${getSourceLabel(topArticle.source)}`} />
                        <Chip label={`Total ${topArticle.scores.total}`} variant="outlined" />
                      </Stack>
                    </Stack>
                    <Typography variant="body1" color="text.secondary">
                      {getSummary(topArticle)}
                    </Typography>
                    <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
                      <Button
                        component="a"
                        href={topArticle.url}
                        target="_blank"
                        rel="noreferrer"
                        endIcon={<OpenInNewIcon />}
                        variant="contained"
                      >
                        元記事を開く
                      </Button>
                      <Typography variant="body2" color="text.secondary" sx={{ alignSelf: 'center' }}>
                        公開: {formatDate(topArticle.publishedAt)}
                      </Typography>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            ) : null}

            {!loading && !error && filteredArticles.length === 0 ? (
              <Alert severity="info">条件に一致する記事がありません。</Alert>
            ) : null}

            <Grid container spacing={2.5}>
              {filteredArticles.map((article) => (
                <Grid key={article.id} size={{ xs: 12, md: 6 }}>
                  <Card data-testid="article-card" sx={{ height: '100%' }}>
                    <CardContent sx={{ height: '100%' }}>
                      <Stack spacing={2} sx={{ height: '100%' }}>
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                          <Chip label={`#${article.rank}`} color="primary" size="small" />
                          <Chip label={getSourceLabel(article.source)} size="small" />
                          <Chip label={`Total ${article.scores.total}`} size="small" variant="outlined" />
                        </Stack>

                        <Box>
                          <Link
                            href={article.url}
                            target="_blank"
                            rel="noreferrer"
                            underline="hover"
                            color="inherit"
                          >
                            <Typography variant="h6">{article.title}</Typography>
                          </Link>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                            {getSummary(article)}
                          </Typography>
                        </Box>

                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                          <Box sx={{ flex: 1 }}>
                            <Stack direction="row" justifyContent="space-between">
                              <Typography variant="caption" color="text.secondary">
                                Tech
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {article.techScore}/30
                              </Typography>
                            </Stack>
                            <LinearProgress
                              variant="determinate"
                              value={(article.techScore / 30) * 100}
                              sx={{ mt: 0.5, height: 8, borderRadius: 999 }}
                            />
                          </Box>
                          <Box sx={{ flex: 1 }}>
                            <Stack direction="row" justifyContent="space-between">
                              <Typography variant="caption" color="text.secondary">
                                Culture
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {article.cultureScore}/30
                              </Typography>
                            </Stack>
                            <LinearProgress
                              color="secondary"
                              variant="determinate"
                              value={(article.cultureScore / 30) * 100}
                              sx={{ mt: 0.5, height: 8, borderRadius: 999 }}
                            />
                          </Box>
                        </Stack>

                        <Grid container spacing={1}>
                          {scoreLabels.map(({ key, label }) => (
                            <Grid key={key} size={{ xs: 6, sm: 4 }}>
                              <Card variant="outlined" sx={{ height: '100%' }}>
                                <CardContent sx={{ py: 1.25, '&:last-child': { pb: 1.25 } }}>
                                  <Typography variant="caption" color="text.secondary">
                                    {label}
                                  </Typography>
                                  <Typography variant="subtitle1">{article.scores[key]} / 10</Typography>
                                </CardContent>
                              </Card>
                            </Grid>
                          ))}
                        </Grid>

                        <Box sx={{ mt: 'auto' }}>
                          <Typography variant="subtitle2" gutterBottom>
                            評価理由
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {article.reason}
                          </Typography>
                          <Stack
                            direction={{ xs: 'column', sm: 'row' }}
                            spacing={1}
                            justifyContent="space-between"
                            sx={{ mt: 2 }}
                          >
                            <Typography variant="caption" color="text.secondary">
                              公開: {formatDate(article.publishedAt)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              更新反映: {formatDate(article.freshnessAt ?? article.publishedAt)}
                            </Typography>
                          </Stack>
                        </Box>
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Stack>
        </Container>
      </Box>
    </ThemeProvider>
  )
}

export default App
