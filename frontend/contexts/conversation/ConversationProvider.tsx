import { type ReactNode, useEffect, useState } from 'react'
import { useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query'

import { useInfiniteMessagesClient } from '@/hooks/useInfiniteMessages'
import { useSources } from '@/hooks/useSources';
import { useStreamResponse } from '@/hooks/useStreamResponse'
import { chatSendErrorMessage } from '@/lib/chatError'
import type { Message } from '@/types/Message'

import { ConversationContext, type ConversationContextValue } from './ConversationContext';

export function ConversationProvider({ children }: { children: ReactNode }) {
    const { conversationId } = useParams<{ conversationId?: string }>()
    const activeConversationId = conversationId ?? ''

    const queryClient = useQueryClient()
    const sourcesResponseObject = useSources(conversationId ?? null)
    const { data: sources = [] } = sourcesResponseObject
    const [unselectedSourcesIds, setUnselectedSourcesIds] = useState<string[]>([])
    const [submittedMessageId, setSubmittedMessageId] = useState<string | null>(null)
    const [localError, setLocalError] = useState<string | null>(null)
    const { upsertMessage } = useInfiniteMessagesClient(queryClient, activeConversationId, 5)
    const stream = useStreamResponse(activeConversationId)

    useEffect(() => {
        if (stream.persistedMessage) {
            upsertMessage(stream.persistedMessage)
        }
    }, [stream.persistedMessage, upsertMessage])

    if (!conversationId) {
        throw new Error('ConversationProvider only can be used in Conversation route')
    }

    const selectedSources = sources.map((source) => source.id).filter((id) => !unselectedSourcesIds.includes(id))

    const handleToogleSelectAllSources = (checked: boolean) => {
        if (checked) {
            setUnselectedSourcesIds([])
            return
        }

        setUnselectedSourcesIds(sources.map((source) => source.id))
    }

    const handleToogleSelectSource = (sourceId: string) => {
        setUnselectedSourcesIds((prev) => (prev.includes(sourceId) ? prev.filter((id) => id !== sourceId) : [...prev, sourceId]))
    }

    const sendMessage = async ({ documentIds, message }: { documentIds: string[]; message: string }) => {
        const messageId = crypto.randomUUID()
        const optimisticMessage: Message = {
            id: messageId,
            conversationId,
            role: 'user',
            text: message,
            createdAt: new Date().toISOString(),
        }
        setLocalError(null)
        setSubmittedMessageId(messageId)
        upsertMessage(optimisticMessage)
        try {
            await stream.sendMessage({ documentIds, message, messageId })
        }
        catch (error) {
            setLocalError(chatSendErrorMessage(error))
            await queryClient.invalidateQueries({ queryKey: ['messages', conversationId] })
        }
    }

    const streamedMessage = (
        stream.streamedMessageId
        && stream.streamedMessageId !== submittedMessageId
        && stream.streamedMessageId !== stream.persistedMessage?.id
    )
        ? {
                id: stream.streamedMessageId,
                conversationId,
                role: 'assistant' as const,
                text: stream.streamedText,
                createdAt: new Date().toISOString(),
            }
        : null
    const streamError = localError
        ?? (stream.error ? chatSendErrorMessage(stream.error) : null)

    const conversationContextObj: ConversationContextValue = {
        conversationId,
        handleToogleSelectAllSources,
        handleToogleSelectSource,
        selectedSources,
        setUnselectedSourcesIds,
        sourcesResponseObject,
        unselectedSourcesIds,
        isPendingMessage: stream.isStreaming,
        sendMessage,
        streamedMessage,
        streamError,
        toolInvocations: stream.toolCalls.map((toolCall) => ({
            id: toolCall.callId,
            name: toolCall.name,
        })),
    }

    return <ConversationContext.Provider value={conversationContextObj}>{children}</ConversationContext.Provider>
}
