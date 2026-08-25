export type MessageSource =
    | { index: number; kind: 'chunk'; chunkId: string }
    | { index: number; kind: 'summary'; documentId: string }
    | { index: number; kind: 'web'; url: string }

export type Message = {
    id: string;
    text: string;
    role: 'user' | 'assistant';
    conversationId: string;
    createdAt: string;
    sources: MessageSource[];
}

export type MessagesParams = {
    before_id?: string;
    limit?: number;
}

export type ChunkPreview = {
    id: string;
    documentId: string;
    filename: string;
    content: string;
    pages: number[] | null;
    chunkIndex: number;
}
