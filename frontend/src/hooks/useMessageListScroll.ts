'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'

import type { Message } from '@/types/Message'

const SCROLL_EPSILON = 2
const ANCHOR_STABLE_FRAMES = 2
const SCROLL_UP_THRESHOLD = 50
const BOTTOM_SCROLL_PADDING = 128

type UseMessageListScrollOptions = {
    messages: Message[];
    isFetchingNextPage: boolean;
    isAiTyping?: boolean;
    streamRevision?: string;
}

function isContainerAtBottom(container: HTMLElement, threshold = SCROLL_EPSILON) {
    return container.scrollHeight - container.scrollTop - container.clientHeight <= threshold
}

function scrollContainerToBottom(container: HTMLElement) {
    container.scrollTop = container.scrollHeight
}

function scrollToLatestMessage(message: Message, container: HTMLElement) {
    if (message.role === 'assistant') {
        const messageEl = container.querySelector(`[data-message-id="${message.id}"]`)
        const availableHeight = container.clientHeight - BOTTOM_SCROLL_PADDING

        if (messageEl instanceof HTMLElement && messageEl.offsetHeight > availableHeight) {
            const top = messageEl.getBoundingClientRect().top
                - container.getBoundingClientRect().top
                + container.scrollTop

            container.scrollTop = top

            return
        }
    }

    scrollContainerToBottom(container)
}

export function useMessageListScroll({
    messages,
    isFetchingNextPage,
    isAiTyping = false,
    streamRevision = '',
}: UseMessageListScrollOptions) {
    const containerRef = useRef<HTMLDivElement>(null)
    const bottomRef = useRef<HTMLDivElement>(null)
    const lastHandledMessageIdRef = useRef<string | null>(null)
    const scrollHeightBeforeFetchRef = useRef<number | null>(null)

    const [isAnchored, setIsAnchored] = useState(false)
    const [userScrolledUp, setUserScrolledUp] = useState(false)

    useEffect(() => {
        if (!isAnchored) {
            return
        }

        const container = containerRef.current

        if (!container) {
            return
        }

        const onScroll = () => {
            setUserScrolledUp(!isContainerAtBottom(container, SCROLL_UP_THRESHOLD))
        }

        container.addEventListener('scroll', onScroll, { passive: true })

        return () => container.removeEventListener('scroll', onScroll)
    }, [isAnchored])

    useLayoutEffect(() => {
        if (messages.length === 0 || isAnchored) {
            return
        }

        const container = containerRef.current
        const bottomEl = bottomRef.current

        if (!container || !bottomEl) {
            return
        }

        let raf = 0
        let stableFrames = 0
        let cancelled = false

        const finish = () => {
            if (cancelled) {
                return
            }

            cancelled = true
            scrollContainerToBottom(container)
            lastHandledMessageIdRef.current = messages.at(-1)?.id ?? null
            setIsAnchored(true)
        }

        const tryAnchor = () => {
            if (cancelled) {
                return
            }

            scrollContainerToBottom(container)
            stableFrames = isContainerAtBottom(container) ? stableFrames + 1 : 0

            if (stableFrames >= ANCHOR_STABLE_FRAMES) {
                finish()

                return
            }

            raf = requestAnimationFrame(tryAnchor)
        }

        const onLayoutChange = () => {
            if (cancelled) {
                return
            }

            stableFrames = 0
            scrollContainerToBottom(container)
        }

        const resizeObserver = new ResizeObserver(onLayoutChange)

        resizeObserver.observe(container)
        resizeObserver.observe(bottomEl)

        void document.fonts.ready.then(() => {
            if (!cancelled) {
                onLayoutChange()
            }
        })

        tryAnchor()

        return () => {
            cancelled = true
            cancelAnimationFrame(raf)
            resizeObserver.disconnect()
        }
    }, [messages, isAnchored])

    useLayoutEffect(() => {
        if (!isAnchored || messages.length === 0) {
            return
        }

        const lastMessage = messages.at(-1)

        if (!lastMessage || lastMessage.id === lastHandledMessageIdRef.current) {
            return
        }

        const container = containerRef.current

        if (!container) {
            return
        }

        lastHandledMessageIdRef.current = lastMessage.id
        scrollToLatestMessage(lastMessage, container)
        setUserScrolledUp(false)
    }, [messages, isAnchored])

    useLayoutEffect(() => {
        if (!isAnchored || !isAiTyping || userScrolledUp) {
            return
        }

        const container = containerRef.current

        if (!container) {
            return
        }

        scrollContainerToBottom(container)
    }, [isAiTyping, isAnchored, streamRevision, userScrolledUp])

    useLayoutEffect(() => {
        const container = containerRef.current

        if (!container) {
            return
        }

        if (isFetchingNextPage) {
            scrollHeightBeforeFetchRef.current = container.scrollHeight

            return
        }

        const previousScrollHeight = scrollHeightBeforeFetchRef.current

        if (previousScrollHeight === null) {
            return
        }

        scrollHeightBeforeFetchRef.current = null

        const diff = container.scrollHeight - previousScrollHeight

        if (diff > 0) {
            container.scrollTop += diff
        }
    }, [isFetchingNextPage, messages.length])

    return {
        containerRef,
        bottomRef,
        isAnchored,
        userScrolledUp,
    }
}
