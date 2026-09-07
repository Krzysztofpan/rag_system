const DATE_LOCALE = 'en-US'

const MINUTE_MS = 60_000
const HOUR_MS = 60 * MINUTE_MS
const DAY_MS = 24 * HOUR_MS
const MONTH_MS = 30 * DAY_MS
const YEAR_MS = 365 * DAY_MS

const relativeTimeFormatter = new Intl.RelativeTimeFormat(DATE_LOCALE, {
    numeric: 'always',
    style: 'long',
})

export const formatDate = (
    value: string,
    options: Intl.DateTimeFormatOptions,
) => new Date(value).toLocaleDateString(DATE_LOCALE, options)

export const formatRelativeTime = (value: string) => {
    const elapsedMs = Math.max(Date.now() - new Date(value).getTime(), 0)

    if (elapsedMs < HOUR_MS) {
        return relativeTimeFormatter.format(
            -Math.max(1, Math.floor(elapsedMs / MINUTE_MS)),
            'minute',
        )
    }
    if (elapsedMs < DAY_MS) {
        return relativeTimeFormatter.format(-Math.floor(elapsedMs / HOUR_MS), 'hour')
    }
    if (elapsedMs < MONTH_MS) {
        return relativeTimeFormatter.format(-Math.floor(elapsedMs / DAY_MS), 'day')
    }
    if (elapsedMs < YEAR_MS) {
        return relativeTimeFormatter.format(-Math.floor(elapsedMs / MONTH_MS), 'month')
    }
    return relativeTimeFormatter.format(-Math.floor(elapsedMs / YEAR_MS), 'year')
}
