import dayjs, { type Dayjs } from 'dayjs'
import 'dayjs/locale/ja'
import { Box, Button } from '@mui/material'
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import { DatePicker } from '@mui/x-date-pickers/DatePicker'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'

type HistoryDateNavigatorProps = {
  historyDates: string[]
  latestDate: string | null
  selectedDate: string | null
  previousDate: string | null
  nextDate: string | null
  loading: boolean
  onSelectDate: (date: string) => void
}

function getHistoryDay(value: string | null): Dayjs | null {
  if (!value) {
    return null
  }
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed : null
}

function getEdgeHistoryDate(historyDates: string[], edge: 'min' | 'max'): string | null {
  if (historyDates.length === 0) {
    return null
  }
  return historyDates.reduce((current, date) => {
    if (edge === 'min') {
      return date < current ? date : current
    }
    return date > current ? date : current
  })
}

export default function HistoryDateNavigator({
  historyDates,
  latestDate,
  selectedDate,
  previousDate,
  nextDate,
  loading,
  onSelectDate,
}: HistoryDateNavigatorProps) {
  const historyDateSet = new Set(historyDates)
  const selectedHistoryDay = getHistoryDay(selectedDate)
  const latestHistoryDay = getHistoryDay(
    latestDate && historyDateSet.has(latestDate) ? latestDate : getEdgeHistoryDate(historyDates, 'max'),
  )
  const earliestHistoryDay = getHistoryDay(getEdgeHistoryDate(historyDates, 'min'))

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale="ja">
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '72px minmax(0, 1fr) 72px',
            sm: '88px minmax(0, 1fr) 88px',
          },
          gap: 1,
          alignItems: 'center',
        }}
      >
        <Button
          variant="outlined"
          size="small"
          onClick={() => previousDate && onSelectDate(previousDate)}
          disabled={!previousDate || loading}
          sx={{ minWidth: 0, px: { xs: 1, sm: 1.5 }, whiteSpace: 'nowrap' }}
        >
          前日
        </Button>

        <DatePicker
          value={selectedHistoryDay}
          onChange={(value) => {
            if (!value) {
              return
            }
            const nextValue = value.format('YYYY-MM-DD')
            if (historyDateSet.has(nextValue)) {
              onSelectDate(nextValue)
            }
          }}
          format="YYYY/MM/DD"
          minDate={earliestHistoryDay ?? undefined}
          maxDate={latestHistoryDay ?? undefined}
          shouldDisableDate={(value) => !historyDateSet.has(value.format('YYYY-MM-DD'))}
          slotProps={{
            textField: {
              size: 'small',
              fullWidth: true,
              inputProps: {
                readOnly: true,
                'aria-label': '表示日',
              },
              sx: {
                minWidth: 0,
                '& .MuiInputBase-input': {
                  px: { xs: 1, sm: 1.5 },
                  textAlign: 'center',
                  cursor: 'pointer',
                  fontSize: { xs: '0.875rem', sm: '1rem' },
                },
              },
            },
          }}
        />

        <Button
          variant="outlined"
          size="small"
          onClick={() => nextDate && onSelectDate(nextDate)}
          disabled={!nextDate || loading}
          sx={{ minWidth: 0, px: { xs: 1, sm: 1.5 }, whiteSpace: 'nowrap' }}
        >
          翌日
        </Button>
      </Box>
    </LocalizationProvider>
  )
}
