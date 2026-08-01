import type { UploadQuality } from './upload'

export type ResourceStatus = 'pending' | 'ready' | 'rejected'

export type Resource = {
    id: string;
    file: File;
    status: ResourceStatus;
    documentId: string | null;
    parsedContent: string | null;
    quality: UploadQuality | null;
    error: string | null;
}
