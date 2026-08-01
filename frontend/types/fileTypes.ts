export const FileTypes = {
    PDF: 'application/pdf',
    DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    MD: 'text/markdown',
    TXT: 'text/plain',
} as const

export type FileType = typeof FileTypes[keyof typeof FileTypes]
