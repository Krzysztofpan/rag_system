export type ChunkMessageSource = {
    index: number;
    kind: 'chunk';
    chunkId: string;
}

export type SummaryMessageSource = {
    index: number;
    kind: 'summary';
    documentId: string;
}

export type WebMessageSource = {
    index: number;
    kind: 'web';
    url: string;
    title: string;
}

export type DocumentMessageSource = ChunkMessageSource | SummaryMessageSource

export type MessageSource = DocumentMessageSource | WebMessageSource

export type CitationPreview = {
    title: string;
    body: string;
}

export type ChunkPreview = {
    id: string;
    documentId: string;
    filename: string;
    content: string;
    pages: number[] | null;
    chunkIndex: number;
}
