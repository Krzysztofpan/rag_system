import { useMemo, useState } from 'react'
import { useStream } from '@langchain/react'

import { createChatStreamAdapter } from '@/services/stream/createChatStreamAdapter'
import type { Message } from '@/types/Message'

type ChatStreamState = {
    documentIds: string[];
    messages: unknown[];
    persistedMessage?: Message;
}

function contentToText(content: unknown): string {
    if (typeof content === 'string') {
        return content
    }
    if (!Array.isArray(content)) {
        return ''
    }
    return content
        .map((block) => {
            if (
                typeof block === 'object'
                && block !== null
                && 'text' in block
            ) {
                const text = (block as { text?: unknown }).text
                return typeof text === 'string' ? text : ''
            }
            return ''
        })
        .join('')
}

export function useStreamResponse(conversationId: string) {
    const adapter = useMemo(
        () => createChatStreamAdapter(conversationId),
        [conversationId],
    )
    const stream = useStream<ChatStreamState>({
        transport: adapter,
        threadId: conversationId,
        initialValues: { documentIds: [], messages: [] },
    })
    const [previousToolCallIds, setPreviousToolCallIds] = useState<Set<string>>(new Set())

    const sendMessage = async ({
        documentIds,
        message,
        messageId,
    }: {
        documentIds: string[];
        message: string;
        messageId: string;
    }) => {
        setPreviousToolCallIds(new Set(
            stream.toolCalls.map((toolCall) => toolCall.callId),
        ))
        await stream.submit(
            {
                messages: [{ id: messageId, type: 'human', content: message }],
                documentIds,
            },
            { multitaskStrategy: 'reject' },
        )
    }

    const lastMessage = stream.messages.at(-1)
    const streamedText = lastMessage ? contentToText(lastMessage.content) : ''
    const currentToolCalls = stream.toolCalls.filter(
        (toolCall) => !previousToolCallIds.has(toolCall.callId),
    )

    return {
        error: stream.error,
        isStreaming: stream.isLoading,
        persistedMessage: stream.values.persistedMessage,
        sendMessage,
        streamedMessageId: lastMessage?.id,
        streamedText,
        toolCalls: currentToolCalls,
    }
}
