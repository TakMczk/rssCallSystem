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
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'
import PublicIcon from '@mui/icons-material/Public'
import UpdateIcon from '@mui/icons-material/Update'
import type { FeedPayload, HistoryIndexPayload } from './types'
import {
  type CategoryMode,
  type SortMode,
  formatDate,
  formatHistoryDate,
  getAdjacentHistoryDate,
  getSourceLabel,
  isFeedPayload,
  isHistoryIndexPayload,
  parseLegacyRssFeed,
  sortArticles,
} from './feedUtils'
import { AboutDialog } from './components/AboutDialog'
import { ArticleCard } from './components/ArticleCard'

type ThemeMode = 'light' | 'dark'
type DataOrigin = 'latest-json' | 'history-json' | 'rss-fallback'
type HistoryMode = 'pending' | 'enabled' | 'disabled'
type ErrorSeverity = 'warning' | 'error'

class HistorySnapshotNotFoundError extends Error {
  constructor(date: string) {
    super(`${formatHistoryDate(date)} の履歴データはまだ保存されていません`)
    this.name = 'HistorySnapshotNotFoundError'
  }
}

async function loadLatestFeed(): Promise<{ payload: FeedPayload; dataOrigin: DataOrigin }> {
  const response = await fetch('./data.json', { cache: 'no-store' })
  if (response.ok) {
    const data: unknown = await response.json()
    if (!isFeedPayload(data)) {
      throw new Error('data.json の形式が想定と異なります')
    }
    return { payload: data, dataOrigin: 'latest-json' }
  }

  const rssResponse = await fetch('./rss.xml', { cache: 'no-store' })
  if (!rssResponse.ok) {
    throw new Error(
      `data.json (${response.status}) と rss.xml (${rssResponse.status}) の取得に失敗しました`,
    )
  }
  const rssText = await rssResponse.text()
  return { payload: parseLegacyRssFeed(rssText), dataOrigin: 'rss-fallback' }
}

async function loadHistoryIndex(): Promise<HistoryIndexPayload | null> {
  const response = await fetch('./history/index.json', { cache: 'no-store' })
  if (response.status === 404) {
    return null
  }
  if (!response.ok) {
    throw new Error(`history/index.json (${response.status}) の取得に失敗しました`)
  }
  const data: unknown = await response.json()
  if (!isHistoryIndexPayload(data)) {
    throw new Error('history/index.json の形式が想定と異なります')
  }
  return data
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
      h5: {
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
  const [errorSeverity, setErrorSeverity] = useState<ErrorSeverity>('error')
  const [historyNotice, setHistoryNotice] = useState<string | null>(null)
  const [dataOrigin, setDataOrigin] = useState<DataOrigin | null>(null)
  const [historyIndex, setHistoryIndex] = useState<HistoryIndexPayload | null>(null)
  const [historyMode, setHistoryMode] = useState<HistoryMode>('pending')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [themeMode, setThemeMode] = useState<ThemeMode>('light')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [sortMode, setSortMode] = useState<SortMode>('recommended')
  const [categoryMode, setCategoryMode] = useState<CategoryMode>('all')
  const [aboutOpen, setAboutOpen] = useState(false)

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

    async function loadIndex() {
      try {
        const data = await loadHistoryIndex()
        if (!active) {
          return
        }
        setHistoryIndex(data)
        setHistoryNotice(null)
        if (data?.latestDate) {
          setSelectedDate((current) =>
            current && data.availableDates.includes(current) ? current : data.latestDate,
          )
          setHistoryMode('enabled')
          return
        }
        setHistoryMode('disabled')
        setSelectedDate(null)
      } catch (err) {
        if (active) {
          setHistoryMode('disabled')
          setSelectedDate(null)
          setHistoryNotice(
            err instanceof Error
              ? `${err.message}。履歴一覧を読めなかったため最新結果を表示します。`
              : '履歴一覧を読み込めなかったため最新結果を表示します。',
          )
        }
      }
    }

    void loadIndex()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let active = true

    async function loadPayload() {
      try {
        setLoading(true)
        setError(null)
        setErrorSeverity('error')

        if (historyMode === 'enabled') {
          if (!selectedDate) {
            return
          }
          const response = await fetch(`./history/${selectedDate}.json`, { cache: 'no-store' })
          if (response.status === 404) {
            throw new HistorySnapshotNotFoundError(selectedDate)
          }
          if (!response.ok) {
            throw new Error(
              `${formatHistoryDate(selectedDate)} の履歴データを読み込めませんでした (${response.status})`,
            )
          }
          const data: unknown = await response.json()
          if (!isFeedPayload(data)) {
            throw new Error(`./history/${selectedDate}.json の形式が想定と異なります`)
          }
          if (active) {
            setPayload(data)
            setDataOrigin('history-json')
          }
          return
        }

        if (historyMode === 'disabled') {
          const latest = await loadLatestFeed()
          if (active) {
            setPayload(latest.payload)
            setDataOrigin(latest.dataOrigin)
          }
        }
      } catch (err) {
        if (active) {
          const message = err instanceof Error ? err.message : '不明なエラーが発生しました'
          setError(message)
          setErrorSeverity(err instanceof HistorySnapshotNotFoundError ? 'warning' : 'error')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    if (historyMode === 'pending') {
      return
    }

    void loadPayload()

    return () => {
      active = false
    }
  }, [historyMode, selectedDate])

  const theme = useMemo(() => createAppTheme(themeMode), [themeMode])

  useEffect(() => {
    if (
      sourceFilter !== 'all' &&
      payload &&
      !payload.articles.some((article) => article.source === sourceFilter)
    ) {
      setSourceFilter('all')
    }
  }, [payload, sourceFilter])

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
  const remainingArticles = topArticle ? filteredArticles.slice(1) : filteredArticles
  const historyDates = historyIndex?.availableDates ?? []
  const previousDate = getAdjacentHistoryDate(historyDates, selectedDate, 'older')
  const nextDate = getAdjacentHistoryDate(historyDates, selectedDate, 'newer')

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
        <AppBar
          position="sticky"
          color="transparent"
          elevation={0}
          sx={{ backdropFilter: 'blur(12px)', borderBottom: '1px solid', borderColor: 'divider' }}
        >
          <Toolbar sx={{ gap: 1.5, flexWrap: 'wrap', py: 1 }}>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Tech Curated Feed
            </Typography>

            <Stack
              direction="row"
              spacing={1}
              useFlexGap
              sx={{ display: { xs: 'none', lg: 'flex' }, flexWrap: 'wrap' }}
            >
              <Chip
                icon={<PublicIcon />}
                label={`記事 ${payload?.articles.length ?? 0}`}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<UpdateIcon />}
                label={payload ? formatDate(payload.generatedAt) : '更新待ち'}
                size="small"
                variant="outlined"
              />
              {selectedDate ? (
                <Chip label={`表示日 ${formatHistoryDate(selectedDate)}`} size="small" variant="outlined" />
              ) : null}
            </Stack>

            <Button
              startIcon={<InfoOutlinedIcon />}
              variant="text"
              color="inherit"
              onClick={() => setAboutOpen(true)}
            >
              About
            </Button>

            <Tooltip title={themeMode === 'dark' ? 'ライトモード' : 'ダークモード'}>
              <IconButton
                color="primary"
                onClick={() => setThemeMode((prev) => (prev === 'dark' ? 'light' : 'dark'))}
              >
                {themeMode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
              </IconButton>
            </Tooltip>

            <Tooltip title="RSS を購読">
              <IconButton
                component="a"
                href="./rss.xml"
                target="_blank"
                rel="noreferrer"
                color="primary"
                aria-label="RSS を購読"
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 2,
                  bgcolor: 'background.paper',
                }}
              >
                <Box component="span" aria-hidden="true" sx={{ fontSize: '1.125rem', lineHeight: 1 }}>
                  📡
                </Box>
              </IconButton>
            </Tooltip>
          </Toolbar>
        </AppBar>

        <AboutDialog
          open={aboutOpen}
          onClose={() => setAboutOpen(false)}
          articleCount={payload?.articles.length ?? 0}
          generatedAt={payload?.generatedAt ?? null}
        />

        <Container maxWidth="lg" sx={{ py: { xs: 2.5, md: 4 } }}>
          <Stack spacing={3}>
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

            {historyNotice ? <Alert severity="info">{historyNotice}</Alert> : null}

            {historyDates.length > 0 ? (
              <Card>
                <CardContent>
                  <Stack spacing={2}>
                    <Box>
                      <Typography variant="overline" color="text.secondary">
                        履歴閲覧
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        最新日を初期表示し、保存済みの日付へ移動できます。
                      </Typography>
                    </Box>

                    <Stack
                      direction={{ xs: 'column', md: 'row' }}
                      spacing={1.5}
                      alignItems={{ xs: 'stretch', md: 'center' }}
                    >
                      <Button
                        variant="outlined"
                        onClick={() => previousDate && setSelectedDate(previousDate)}
                        disabled={!previousDate || loading}
                      >
                        前日
                      </Button>

                      <FormControl
                        size="small"
                        sx={{ width: { xs: '100%', md: 'auto' }, minWidth: { md: 220 } }}
                      >
                        <InputLabel id="history-date-label">表示日</InputLabel>
                        <Select
                          labelId="history-date-label"
                          label="表示日"
                          value={selectedDate ?? ''}
                          onChange={(event) => setSelectedDate(event.target.value)}
                        >
                          {historyDates.map((date) => (
                            <MenuItem key={date} value={date}>
                              {formatHistoryDate(date)}
                              {date === historyIndex?.latestDate ? ' (最新)' : ''}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>

                      <Button
                        variant="outlined"
                        onClick={() => nextDate && setSelectedDate(nextDate)}
                        disabled={!nextDate || loading}
                      >
                        翌日
                      </Button>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            ) : null}

            {error ? <Alert severity={errorSeverity}>{error}</Alert> : null}

            {!loading && !error && dataOrigin === 'rss-fallback' ? (
              <Alert severity="info">
                `data.json` が未生成のため、現在は `rss.xml` から互換表示しています。次回パイプライン実行後は
                `data.json` の内容を優先して読み込みます。
              </Alert>
            ) : null}

            {!loading && !error ? (
              <Box
                sx={{
                  p: { xs: 2, md: 2.5 },
                  borderRadius: '18px',
                  bgcolor: (theme) =>
                    theme.palette.mode === 'dark'
                      ? 'rgba(144,202,249,0.08)'
                      : 'rgba(21,101,192,0.05)',
                  border: '1px solid',
                  borderColor: 'divider',
                }}
              >
                <Stack spacing={1.5}>
                  <Typography variant="overline" color="text.secondary">
                    絞り込みと並び替え
                  </Typography>

                  <Stack
                    direction={{ xs: 'column', md: 'row' }}
                    spacing={2}
                    alignItems={{ xs: 'stretch', md: 'center' }}
                  >
                    <FormControl
                      size="small"
                      sx={{ width: { xs: '100%', md: 'auto' }, minWidth: { md: 220 } }}
                    >
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

                    <FormControl
                      size="small"
                      sx={{ width: { xs: '100%', md: 'auto' }, minWidth: { md: 180 } }}
                    >
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
              </Box>
            ) : null}

            {!loading && !error && filteredArticles.length === 0 ? (
              <Alert severity="info">条件に一致する記事がありません。</Alert>
            ) : null}

            {!loading && !error && topArticle ? (
              <Stack spacing={2}>
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  spacing={1}
                  justifyContent="space-between"
                  alignItems={{ xs: 'flex-start', sm: 'center' }}
                >
                  <Box>
                    <Typography variant="h5">注目記事</Typography>
                    <Typography variant="body2" color="text.secondary">
                      まず確認したい 1 本を、要点とスコアをまとめて表示します。
                    </Typography>
                  </Box>
                  <Chip label={`表示中 ${filteredArticles.length}件`} variant="outlined" />
                </Stack>
                <ArticleCard article={topArticle} featured />
              </Stack>
            ) : null}

            {!loading && !error && remainingArticles.length > 0 ? (
              <Stack spacing={2}>
                <Box>
                  <Typography variant="h5">記事一覧</Typography>
                  <Typography variant="body2" color="text.secondary">
                    概要と評価理由を見ながら、読む価値がある記事をすばやく選べます。
                  </Typography>
                </Box>
                <Grid container spacing={2.5}>
                  {remainingArticles.map((article) => (
                    <Grid key={article.id} size={{ xs: 12, lg: 6 }}>
                      <ArticleCard article={article} />
                    </Grid>
                  ))}
                </Grid>
              </Stack>
            ) : null}
          </Stack>
        </Container>
      </Box>
    </ThemeProvider>
  )
}

export default App
