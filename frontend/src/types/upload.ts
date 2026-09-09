export type ParseIssue = {
    line: number;
    kinds: string[];
    text: string;
}

export type ParseReport = {
    ok: boolean;
    counts: Record<string, number>;
    issues: ParseIssue[];
}

export type RejectedChunk = {
    index: number;
    kinds: string[];
    text: string;
}

export type ChunkQuality = {
    ok: boolean;
    totalChunks: number;
    keptChunks: number;
    rejectedChunks: number;
    rejectedRatio: number;
    maxRejectedRatio: number;
    rejected: RejectedChunk[];
}

export type UploadQuality = {
    parseReport: ParseReport;
    chunkQuality: ChunkQuality;
}
