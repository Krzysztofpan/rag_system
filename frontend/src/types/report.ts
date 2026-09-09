import type { UploadQuality } from './upload'

export type SourceReport = {
    documentId: string;
    parsedContent: string | null;
    summary: string | null;
    quality: UploadQuality | null;
}
