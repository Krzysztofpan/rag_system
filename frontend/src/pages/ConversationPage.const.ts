import type { Conversation } from '@/types/conversation';

export const items = [
    { label: 'Newest updated', value: 0, method: (a: Conversation, b: Conversation) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime() },
    { label: 'Newest', value: 1, method: (a: Conversation, b: Conversation) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime() },
    { label: 'Oldest', value: 2, method: (a: Conversation, b: Conversation) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime() },
    { label: 'By title', value: 3, method: (a: Conversation, b: Conversation) => a.title.localeCompare(b.title) },
]
