import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Link,
  Stack,
  Typography,
} from '@mui/material'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import type { FeedArticle } from '../types'
import { formatDate, getDisplayTitle, getSummary } from '../feedUtils'
import { SourceBadge } from './SourceBadge'

const scoreLabels = [
  { key: 'novelty', label: '新規性', shortLabel: '新規' },
  { key: 'interest', label: '興味性', shortLabel: '興味' },
  { key: 'expertise', label: '専門性', shortLabel: '専門' },
  { key: 'culturalRelevance', label: '文化関連性', shortLabel: '文化' },
  { key: 'lifestyleConnection', label: '生活接続性', shortLabel: '生活' },
  { key: 'creativity', label: '創造性', shortLabel: '創造' },
] as const

type ArticleCardProps = {
  article: FeedArticle
  featured?: boolean
}

export function ArticleCard({ article, featured = false }: ArticleCardProps) {
  return (
    <Card
      data-testid={featured ? 'featured-article-card' : 'article-card'}
      sx={{
        height: '100%',
        border: featured ? 1 : undefined,
        borderColor: featured ? 'secondary.main' : undefined,
      }}
    >
      <CardContent sx={{ minWidth: 0 }}>
        <Stack spacing={2.25} sx={{ minWidth: 0 }}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            justifyContent="space-between"
            alignItems={{ xs: 'flex-start', sm: 'center' }}
          >
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
              <Chip
                label={`#${article.rank}`}
                size="small"
                color="warning"
                sx={{ fontWeight: 700 }}
              />
              <SourceBadge source={article.source} />
              {featured ? <Chip label="注目記事" size="small" color="secondary" variant="outlined" /> : null}
            </Stack>
            <Typography variant="caption" color="text.secondary">
              公開: {formatDate(article.publishedAt)}
            </Typography>
          </Stack>

          <Box>
            <Link
              href={article.url}
              target="_blank"
              rel="noreferrer"
              underline="hover"
              color="inherit"
            >
              <Typography
                variant={featured ? 'h5' : 'h6'}
                sx={{ overflowWrap: 'anywhere', wordBreak: 'break-word' }}
              >
                {getDisplayTitle(article)}
              </Typography>
            </Link>
          </Box>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: 'minmax(0,1fr) 220px' },
              gap: 2,
              alignItems: 'start',
              minWidth: 0,
            }}
          >
            <Stack spacing={1.75} sx={{ minWidth: 0 }}>
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  概要
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ lineHeight: 1.8, overflowWrap: 'anywhere', wordBreak: 'break-word' }}
                >
                  {getSummary(article)}
                </Typography>
              </Box>

              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  選定理由
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ lineHeight: 1.7, overflowWrap: 'anywhere', wordBreak: 'break-word' }}
                >
                  {article.reason}
                </Typography>
              </Box>

              {featured ? (
                <Button
                  component="a"
                  href={article.url}
                  target="_blank"
                  rel="noreferrer"
                  endIcon={<OpenInNewIcon />}
                  variant="contained"
                  sx={{ alignSelf: 'flex-start' }}
                >
                  元記事を開く
                </Button>
              ) : null}
            </Stack>

            <Box
              sx={{
                p: 1.5,
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: '16px',
                bgcolor: (theme) =>
                  theme.palette.mode === 'dark'
                    ? 'rgba(144,202,249,0.08)'
                    : 'rgba(21,101,192,0.04)',
                minWidth: 0,
              }}
            >
              <Stack spacing={1.1}>
                <Stack direction="row" justifyContent="space-between" alignItems="baseline">
                  <Typography variant="overline" color="text.secondary">
                    Score
                  </Typography>
                  <Typography variant="h6" sx={{ lineHeight: 1 }}>
                    {article.scores.total}
                    <Typography component="span" variant="body2" color="text.secondary">
                      /60
                    </Typography>
                  </Typography>
                </Stack>

                <Box>
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

                <Box>
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

                <Box sx={{ pb: 0.25 }}>
                  <Stack
                    direction="row"
                    spacing={0.75}
                    useFlexGap
                    sx={{
                      flexWrap: 'wrap',
                      minWidth: 0,
                      justifyContent: { xs: 'flex-start', md: 'center' },
                    }}
                  >
                    {scoreLabels.map(({ key, label, shortLabel }) => (
                      <Box
                        key={key}
                        title={`${label}: ${article.scores[key]} / 10`}
                        sx={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 0.5,
                          px: 0.9,
                          py: 0.55,
                          border: '1px solid',
                          borderColor: 'divider',
                          borderRadius: '10px',
                          bgcolor: 'background.paper',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          {shortLabel}
                        </Typography>
                        <Typography variant="caption" sx={{ fontWeight: 700 }}>
                          {article.scores[key]}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Box>
              </Stack>
            </Box>
          </Box>

          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            justifyContent="space-between"
          >
            <Typography variant="caption" color="text.secondary">
              更新反映: {formatDate(article.freshnessAt ?? article.publishedAt)}
            </Typography>
            {!featured ? (
              <Button
                component="a"
                href={article.url}
                target="_blank"
                rel="noreferrer"
                variant="outlined"
                size="small"
                endIcon={<OpenInNewIcon />}
                sx={{ alignSelf: { xs: 'flex-start', sm: 'center' } }}
              >
                元記事を開く
              </Button>
            ) : null}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}
