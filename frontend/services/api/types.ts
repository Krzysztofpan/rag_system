import type { Conversation } from '@/types/conversation'
import type { Message } from '@/types/Message';
import type { SourceReport } from '@/types/report'
import type { Source } from '@/types/source'

export type GetConversationResponse = {
    conversations: Conversation[];
}

export type CreateConversationResponse = {
    conversationId: string;
    userId: string;
}

export type DeleteConversationResponse = {
    deletedConversation: Conversation;
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
