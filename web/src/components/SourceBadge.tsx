import { useMemo, useState } from 'react'
import { Box, Typography } from '@mui/material'
import { getSourceLabel } from '../feedUtils'

type SourceBadgeProps = {
  source: string
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const [failedFaviconUrl, setFailedFaviconUrl] = useState<string | null>(null)
  const faviconUrl = useMemo(() => {
    try {
      return new URL('/favicon.ico', source).toString()
    } catch {
      return null
    }
  }, [source])
  const showFavicon = Boolean(faviconUrl) && failedFaviconUrl !== faviconUrl

  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 0.75,
        px: 1,
        py: 0.5,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 999,
        bgcolor: 'background.paper',
        minHeight: 28,
      }}
    >
      {showFavicon && faviconUrl ? (
        <Box
          component="img"
          src={faviconUrl}
          alt=""
          onError={() => setFailedFaviconUrl(faviconUrl)}
          sx={{ width: 16, height: 16, borderRadius: 0.5, flexShrink: 0 }}
        />
      ) : null}
      <Typography variant="caption" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
        {getSourceLabel(source)}
      </Typography>
    </Box>
  )
}
