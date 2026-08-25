import type { MessageSource } from './citation'

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
