import { useCallback, useEffect, useState } from 'react'

import type { ConversationTopicName } from '@/lib/conversationTopic'
import { parseConversationUpdatedEvent, readSseDataFrames } from '@/lib/sse'
import { apiService } from '@/services/api/apiService'
import type { Source } from '@/types/source'

import { useConversationsClient } from './useConversations'

const RECONNECT_MS = 1500
const CONVERSATION_EVENTS_IDLE_MS = 30_000

function isAbortError(error: unknown): boolean {
    return error instanceof DOMException && error.name === 'AbortError'
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve, reject) => {
        if (signal.aborted) {
            reject(signal.reason instanceof Error ? signal.reason : new DOMException('Aborted', 'AbortError'))
            return
        }
        const timeout = window.setTimeout(resolve, ms)
        signal.addEventListener('abort', () => {
            window.clearTimeout(timeout)
            reject(signal.reason instanceof Error ? signal.reason : new DOMException('Aborted', 'AbortError'))
        }, { once: true })
    })
}

async function listenForConversationUpdates(
    conversationId: string,
    signal: AbortSignal,
    onUpdated: (title: string, topic: ConversationTopicName) => void,
): Promise<void> {
    while (!signal.aborted) {
        try {
            const response = await apiService.streamConversationEvents(conversationId, { signal })
            if (response.status === 401 || response.status === 404) {
                return
            }
            if (!response.ok || response.body === null) {
                await delay(RECONNECT_MS, signal)
                continue
            }

            await readSseDataFrames(response.body, (data) => {
                const event = parseConversationUpdatedEvent(data)
                if (event?.conversationId === conversationId) {
                    onUpdated(event.title, event.topic)
                }
            })
            if (signal.aborted) {
                return
            }
            await delay(RECONNECT_MS, signal)
        }
        catch (error) {
            if (signal.aborted || isAbortError(error)) {
                return
            }
            await delay(RECONNECT_MS, signal)
        }
    }
}

export function useConversationEvents(
    conversationId: string | undefined,
    sources: Source[],
) {
    const { patchConversation } = useConversationsClient()
    const [armed, setArmed] = useState(false)
    const sourceInFlight = sources.some(
        (source) => source.status === 'pending' || source.status === 'processing',
    )
    const armConversationEvents = useCallback(() => {
        setArmed(true)
    }, [])

    useEffect(() => {
        const activeConversationId = armed ? conversationId : undefined
        if (!activeConversationId) {
            return
        }

        const controller = new AbortController()
        void listenForConversationUpdates(activeConversationId, controller.signal, (title, topic) => {
            patchConversation(activeConversationId, {
                title,
                topic,
                updatedAt: new Date().toISOString(),
            })
        })

        return () => {
            controller.abort()
        }
    }, [armed, conversationId, patchConversation])

    useEffect(() => {
        if (!armed || sourceInFlight) {
            return
        }
        const timeout = window.setTimeout(() => {
            setArmed(false)
        }, CONVERSATION_EVENTS_IDLE_MS)
        return () => {
            window.clearTimeout(timeout)
        }
    }, [armed, sourceInFlight])

    return armConversationEvents
}
