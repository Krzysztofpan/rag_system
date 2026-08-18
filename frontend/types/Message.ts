export type Message = {
    id: string;
    text: string;
    role: 'user' | 'assistant';
    conversationId: string;
    createdAt: string;
}

export type MessagesParams = {
    before_id?: string;
    limit?: number;
}
