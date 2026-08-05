export type SourceStatus = 'pending' | 'processing' | 'ready' | 'failed'

export type Source = {
    id: string;
    filename: string;
    contentType: string | null;
    status: SourceStatus;
    error: string | null;
    chunkCount: number;
}
