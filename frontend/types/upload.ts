/**
 * Odwzorowanie odpowiedzi backendu POST /upload.
 * Nazwy pól celowo zostają w snake_case — to surowy kształt JSON-a z FastAPI.
 */

/** Pozycja z audytu markdownu: audit_markdown() w quality_audit.py */
export type ParseIssue = {
    line: number;
    kinds: string[];
    text: string;
}

export type ParseReport = {
    ok: boolean;
    /** Liczba wystąpień per rodzaj defektu, np. { unresolved_glyph: 3 } */
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
    total_chunks: number;
    kept_chunks: number;
    rejected_chunks: number;
    rejected_ratio: number;
    max_rejected_ratio: number;
    rejected: RejectedChunk[];
}

export type UploadQuality = {
    parse_report: ParseReport;
    chunk_quality: ChunkQuality;
}

/** Jednolity kształt odpowiedzi POST /upload (zawsze HTTP 200). */
export type UploadResourceResponse = {
    status: 'ready' | 'rejected';
    document_id: string | null;
    parsed_content: string | null;
    quality: UploadQuality | null;
    error: string | null;
}
