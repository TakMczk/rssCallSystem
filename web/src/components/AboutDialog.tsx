import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Stack,
  Typography,
} from '@mui/material'
import { formatDate } from '../feedUtils'

type AboutDialogProps = {
  open: boolean
  onClose: () => void
  articleCount: number
  generatedAt: string | null
}

export function AboutDialog({
  open,
  onClose,
  articleCount,
  generatedAt,
}: AboutDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>About Tech Curated Feed</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2.5}>
          <Typography variant="body1" color="text.secondary">
            技術記事を、読む前に判断しやすくするためのビューです。各記事に対して日本語概要、Tech /
            Culture の内訳、選定理由をまとめて表示します。
          </Typography>

          <Divider />

          <Stack spacing={1}>
            <Typography variant="subtitle1">表示内容</Typography>
            <Typography variant="body2" color="text.secondary">
              タイトルだけでなく、概要、評価理由、Tech / Culture スコア、各評価項目の内訳をカード形式で一覧できます。
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="subtitle1">収集元</Typography>
            <Typography variant="body2" color="text.secondary">
              Qiita / Zenn / CodeZine に加え、Hacker News、Lobsters、Ars Technica、The Verge
              などの海外ソースを巡回します。
            </Typography>
          </Stack>

          <Stack spacing={1}>
            <Typography variant="subtitle1">現在の状態</Typography>
            <Typography variant="body2" color="text.secondary">
              記事数: {articleCount}件
            </Typography>
            <Typography variant="body2" color="text.secondary">
              最終更新: {generatedAt ? formatDate(generatedAt) : '取得中'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              最新表示は `docs/data.json` と `docs/rss.xml` を使い、日別履歴は
              `docs/history/YYYY-MM-DD.json` と `docs/history/index.json` として公開します。
            </Typography>
          </Stack>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>閉じる</Button>
      </DialogActions>
    </Dialog>
  )
}
