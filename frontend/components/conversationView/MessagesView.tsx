import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { flattenMessagePages, useInfiniteMessages, useInfiniteScrollSentinel } from '@/hooks/useInfiniteMessages'
import { useMessageListScroll } from '@/hooks/useMessageListScroll'

import { Skeleton } from '../ui/skeleton'
import MessageItem from './MessageItem'
import TypingIndicator from './TypingIndicator'

const MessagesView = ({ conversationId }: { conversationId: string }) => {
    const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteMessages(conversationId, 5)
    const messages = flattenMessagePages(data?.pages)

    const { containerRef, bottomRef, isAnchored } = useMessageListScroll({
        messages,
        isFetchingNextPage,
    })
    const { isPendingMessage } = useConversationContext()

    const topSentinelRef = useInfiniteScrollSentinel({
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
        enabled: isAnchored,
        rootRef: containerRef,
        rootMargin: '200px 0px 0px 0px',
    })

    return (
        <div className="overflow-y-auto overflow-anchor-none flex justify-center flex-1" ref={containerRef}>
            <div className="flex min-h-0 max-w-4xl flex-1 flex-col gap-8">
                {hasNextPage && <div ref={topSentinelRef} aria-hidden className="h-px shrink-0" />}
                {isFetchingNextPage && (
                    <div className="space-y-8">
                        <Skeleton className="h-12 w-3/4 rounded-full" />
                        <Skeleton className="ml-auto h-12 w-1/2 rounded-full" />
                    </div>
                )}
                {messages.map((message) => (
                    <div key={message.id} data-message-id={message.id} className="scroll-mt-4">
                        <MessageItem message={message} />
                    </div>
                ))}
                {isPendingMessage
                    && (
                        <div key="pending" data-message-id="pending" className="scroll-mt-4">
                            <TypingIndicator />
                        </div>
                    )}
                <div ref={bottomRef} aria-hidden className="h-px shrink-0 scroll-mb-32" />
            </div>
        </div>
    )
}

export default MessagesView
