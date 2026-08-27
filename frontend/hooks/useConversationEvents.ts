import { useCallback, useEffect, useState } from 'react'

import { parseConversationTitleEvent, readSseDataFrames } from '@/lib/sse'
import { apiService } from '@/services/api/apiService'
import type { Source } from '@/types/source'

import { useConversationsClient } from './useConversations'

const RECONNECT_MS = 1500
const TITLE_EVENTS_IDLE_MS = 30_000

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

async function listenForConversationTitle(
    conversationId: string,
    signal: AbortSignal,
    onTitle: (title: string) => void,
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
                const event = parseConversationTitleEvent(data)
                if (event?.conversationId === conversationId) {
                    onTitle(event.title)
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
    const { editConversationTitle } = useConversationsClient()
    const [armed, setArmed] = useState(false)
    const sourceInFlight = sources.some(
        (source) => source.status === 'pending' || source.status === 'processing',
    )
    const armConversationTitleEvents = useCallback(() => {
        setArmed(true)
    }, [])

    useEffect(() => {
        const activeConversationId = armed ? conversationId : undefined
        if (!activeConversationId) {
            return
        }

        const controller = new AbortController()
        void listenForConversationTitle(activeConversationId, controller.signal, (title) => {
            editConversationTitle(activeConversationId, title)
        })

        return () => {
            controller.abort()
        }
    }, [armed, conversationId, editConversationTitle])

    useEffect(() => {
        if (!armed || sourceInFlight) {
            return
        }
        const timeout = window.setTimeout(() => {
            setArmed(false)
        }, TITLE_EVENTS_IDLE_MS)
        return () => {
            window.clearTimeout(timeout)
        }
    }, [armed, sourceInFlight])

    return armConversationTitleEvents
}
