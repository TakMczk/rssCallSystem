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
import type { FeedPayload } from './types'
import {
  type CategoryMode,
  type SortMode,
  formatDate,
  getSourceLabel,
  isFeedPayload,
  parseLegacyRssFeed,
  sortArticles,
} from './feedUtils'
import { AboutDialog } from './components/AboutDialog'
import { ArticleCard } from './components/ArticleCard'

type ThemeMode = 'light' | 'dark'
type DataOrigin = 'json' | 'rss-fallback'

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
  const [dataOrigin, setDataOrigin] = useState<DataOrigin | null>(null)
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
  const remainingArticles = topArticle ? filteredArticles.slice(1) : filteredArticles

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

            {error ? <Alert severity="error">{error}</Alert> : null}

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
