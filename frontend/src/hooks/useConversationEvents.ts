import { useCallback, useEffect, useState } from 'react'

import type { ConversationTopicName } from '@/lib/conversationTopic'
import { parseConversationUpdatedEvent, parseResourceUpdatedEvent, readSseDataFrames } from '@/lib/sse'
import { apiService } from '@/services/api/apiService'
import type { Source } from '@/types/source'

import { useConversationsClient } from './useConversations'
import { useResourcesClient } from './useResources'

const RECONNECT_MS = 1500
const CONVERSATION_EVENTS_IDLE_MS = 30_000
const RESOURCE_TITLE_WAIT_MS = 90_000

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

type ConversationEventHandlers = {
    onConversationUpdated: (
        title: string,
        topic: ConversationTopicName,
        documentsSummary: string | null,
    ) => void;
    onResourceUpdated: (resourceId: string, title: string) => void;
}

async function listenForConversationUpdates(
    conversationId: string,
    signal: AbortSignal,
    handlers: ConversationEventHandlers,
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
                const conversationEvent = parseConversationUpdatedEvent(data)
                if (conversationEvent?.conversationId === conversationId) {
                    handlers.onConversationUpdated(
                        conversationEvent.title,
                        conversationEvent.topic,
                        conversationEvent.documentsSummary,
                    )
                    return
                }
                const resourceEvent = parseResourceUpdatedEvent(data)
                if (resourceEvent?.conversationId === conversationId) {
                    handlers.onResourceUpdated(resourceEvent.resourceId, resourceEvent.title)
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
    const { patchResourceTitle } = useResourcesClient(conversationId ?? '')
    const [armed, setArmed] = useState(false)
    const [pendingResourceIds, setPendingResourceIds] = useState<string[]>([])
    const sourceInFlight = sources.some(
        (source) => source.status === 'pending' || source.status === 'processing',
    )
    const resourceTitleInFlight = pendingResourceIds.length > 0
    const armConversationEvents = useCallback((resourceId?: string) => {
        setArmed(true)
        if (!resourceId) {
            return
        }
        setPendingResourceIds((current) => (
            current.includes(resourceId) ? current : [...current, resourceId]
        ))
    }, [])

    useEffect(() => {
        const activeConversationId = armed ? conversationId : undefined
        if (!activeConversationId) {
            return
        }

        const controller = new AbortController()
        void listenForConversationUpdates(activeConversationId, controller.signal, {
            onConversationUpdated: (title, topic, documentsSummary) => {
                patchConversation(activeConversationId, {
                    title,
                    topic,
                    documentsSummary,
                    updatedAt: new Date().toISOString(),
                })
            },
            onResourceUpdated: (resourceId, title) => {
                patchResourceTitle(resourceId, title)
                setPendingResourceIds((current) => current.filter((id) => id !== resourceId))
            },
        })

        return () => {
            controller.abort()
        }
    }, [armed, conversationId, patchConversation, patchResourceTitle])

    useEffect(() => {
        if (!armed || sourceInFlight || resourceTitleInFlight) {
            return
        }
        const timeout = window.setTimeout(() => {
            setArmed(false)
        }, CONVERSATION_EVENTS_IDLE_MS)
        return () => {
            window.clearTimeout(timeout)
        }
    }, [armed, resourceTitleInFlight, sourceInFlight])

    useEffect(() => {
        if (!resourceTitleInFlight) {
            return
        }
        const timeout = window.setTimeout(() => {
            setPendingResourceIds([])
        }, RESOURCE_TITLE_WAIT_MS)
        return () => {
            window.clearTimeout(timeout)
        }
    }, [resourceTitleInFlight])

    return armConversationEvents
}
