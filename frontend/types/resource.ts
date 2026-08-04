export type ResourceStatus = 'pending' | 'processing' | 'ready' | 'failed'

export type Resource = {
    id: string;
    filename: string;
    contentType: string | null;
    status: ResourceStatus;
    error: string | null;
    chunkCount: number;
}
