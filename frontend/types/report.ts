import type { UploadQuality } from './upload'

export type ResourceReport = {
    documentId: string;
    parsedContent: string | null;
    quality: UploadQuality | null;
}
