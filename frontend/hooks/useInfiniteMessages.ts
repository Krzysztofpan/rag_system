'use client'

import { type RefObject, useEffect, useRef } from 'react'
import { type InfiniteData, infiniteQueryOptions, QueryClient, useInfiniteQuery } from '@tanstack/react-query'

import { apiService } from '@/services/api/apiService'
import type { GetMessagesResponse } from '@/services/api/types'
import type { Message, MessagesParams } from '@/types/Message'

export type MessagesCursor = Pick<MessagesParams, 'before_id'>

export function flattenInfinitePages<TItem, TPage>(
    pages: TPage[] | undefined,
    selectItems: (page: TPage) => TItem[],
    options?: { prependPages?: boolean },
): TItem[] {
    if (!pages) {
        return []
    }

    const orderedPages = options?.prependPages ? [...pages].reverse() : pages

    return orderedPages.flatMap(selectItems)
}


export function flattenMessagePages(pages: GetMessagesResponse[] | undefined) {
    return flattenInfinitePages(pages, (page) => page.messages, { prependPages: true })
}

type UseInfiniteScrollSentinelOptions = {
    fetchNextPage: () => Promise<unknown>;
    hasNextPage: boolean | undefined;
    isFetchingNextPage: boolean;
    enabled?: boolean;
    rootRef?: RefObject<Element | null>;
    scrollRootSelector?: string;
    rootMargin?: string;
}

export function useInfiniteScrollSentinel({
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    enabled = true,
    rootRef,
    scrollRootSelector,
    rootMargin = '100px',
}: UseInfiniteScrollSentinelOptions) {
    const sentinelRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (!enabled) {
            return
        }

        const sentinel = sentinelRef.current

        if (!sentinel) {
            return
        }

        const scrollRoot = rootRef?.current ?? (scrollRootSelector ? sentinel.closest(scrollRootSelector) : null)

        const observer = new IntersectionObserver(
            (entries) => {
                const entry = entries[0]

                if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
                    void fetchNextPage()
                }
            },
            {
                root: scrollRoot,
                rootMargin,
                threshold: 0,
            },
        )

        observer.observe(sentinel)

        return () => observer.disconnect()
    }, [enabled, fetchNextPage, hasNextPage, isFetchingNextPage, rootRef, scrollRootSelector, rootMargin])

    return sentinelRef
}


export function getMessagesNextPageParam(lastPage: GetMessagesResponse): MessagesCursor | undefined {
    if (!lastPage.hasMore) {
        return undefined
    }

    const oldestInPage = lastPage.messages[0]

    if (!oldestInPage) {
        return undefined
    }

    return {
        before_id: oldestInPage.id,
    }
}

function messagesInfiniteQueryOptions(conversationId: string, limit = 10) {
    return infiniteQueryOptions({
        queryKey: ['messages', conversationId, limit] as const,
        queryFn: ({ pageParam }) =>
            apiService.getMessages(conversationId, {
                limit,
                ...(pageParam ?? {}),
            }),
        initialPageParam: undefined as MessagesCursor | undefined,
        getNextPageParam: getMessagesNextPageParam,
        enabled: Boolean(conversationId),
    })
}

export function useInfiniteMessages(conversationId: string, limit = 10) {
    return useInfiniteQuery(messagesInfiniteQueryOptions(conversationId, limit))
}

export const useInfiniteMessagesClient = (queryClient: QueryClient, conversationId: string, limit: number) => {
    const addNewMessage = (newMessage: Message) => {
        queryClient.setQueryData<InfiniteData<GetMessagesResponse>>(['messages', conversationId, limit], (messages) => {
            if (!messages?.pages.length) {
                const messages = [newMessage]
                return {
                    pages: [{ messages, hasMore: false }],
                    pageParams: [undefined],
                }
            }
            const pages = [...messages.pages]
            const firstPage = pages[0]

            pages[0] = {
                ...firstPage,
                messages: [...firstPage.messages, newMessage],
            }

            return { ...messages, pages }
        })
    }


    return { addNewMessage }
}
