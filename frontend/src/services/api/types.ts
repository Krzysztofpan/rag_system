
import type { ChunkPreview } from '@/types/citation'
import type { Conversation } from '@/types/conversation'
import type { Message } from '@/types/Message'
import type { SourceReport } from '@/types/report'
import type { Source } from '@/types/source'

export type GetConversationResponse = {
    conversations: Conversation[];
}

export type ConversationResponse = Conversation

export type CreateConversationResponse = {
    conversationId: string;
    userId: string;
}

export type DeleteConversationResponse = {
    deletedConversation: Conversation;
}

export type ResourceType = 'note' | 'mind_map'

export type NoteContent = {
    text?: string;
}

export type Resource = {
    id: string;
    type: ResourceType;
    content: NoteContent | Record<string, unknown>;
    title: string;
    createdAt: string;
    updatedAt: string;
}

export type GetResourcesResponse = {
    count: number;
    conversationResources: Resource[];
}

export type SourceResponse = Source

export type GetSourcesResponse = {
    count: number;
    conversationSources: SourceResponse[];
}

export type DeleteSourceResponse = {
    deletedDocument: Source;
}

export type SourceReportResponse = SourceReport

export type GetMessagesResponse = {
    messages: Message[];
    hasMore: boolean;
}

export type SendMessageResponse = {
    response: Message;
}

export type ChunkResponse = ChunkPreview
