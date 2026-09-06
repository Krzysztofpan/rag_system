const DATE_LOCALE = 'en-US'

export const formatDate = (
    value: string,
    options: Intl.DateTimeFormatOptions,
) => new Date(value).toLocaleDateString(DATE_LOCALE, options)
