export const FileTypes = {
    PDF: 'application/pdf',
    DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    MD: 'text/markdown',
    TXT: 'text/plain',
    PNG: 'image/png',
    JPEG: 'image/jpeg',
} as const

export type FileType = typeof FileTypes[keyof typeof FileTypes]
