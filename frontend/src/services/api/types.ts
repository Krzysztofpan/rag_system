
import type { ChunkPreview, MessageSource } from '@/types/citation'
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

export type ChatNoteContent = {
    kind: 'chat';
    markdown: string;
    messageId?: string;
    sources?: MessageSource[];
}

export type UserNoteContent = {
    kind: 'user';
    html: string;
}

export type NoteContent = ChatNoteContent | UserNoteContent

export type MindMapContent = Record<string, unknown>

type ResourceBase = {
    id: string;
    title: string;
    createdAt: string;
    updatedAt: string;
}

export type NoteResource = ResourceBase & {
    type: 'note';
    content: NoteContent;
}

export type MindMapResource = ResourceBase & {
    type: 'mind_map';
    content: MindMapContent;
}

export type Resource = NoteResource | MindMapResource

export type GetResourcesResponse = {
    count: number;
    conversationResources: Resource[];
}

export type CreateNoteRequest = {
    title?: string;
    content?: NoteContent;
}

export type UpdateNoteRequest = {
    content?: UserNoteContent;
    title?: string;
}

export type CreateNoteResponse = {
    resource: NoteResource;
}

export type UpdateNoteResponse = CreateNoteResponse

export type DeleteResourceResponse = {
    deletedResource: Resource;
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
