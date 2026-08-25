import { cn } from '@/lib/utils'
import type { Message } from '@/types/Message'

import MarkdownContent from './MarkdownContent'
import MessageCitation from './messageCitation/MessageCitation'

const MessageItem = ({ message }: { message: Message }) => {
    const isUser = message.role === 'user'

    return (
        <div className={cn('flex w-full px-3 py-3', isUser ? 'justify-end font-semibold' : 'font-normal')}>
            {isUser
                ? <p className="max-w-2/3 break-all rounded-3xl bg-mist-300 px-5 py-3">{message.text}</p>
                : (
                        <div className="flex max-w-full flex-col gap-3">
                            <MarkdownContent
                                content={message.text}
                                className="max-w-full"
                                conversationId={message.conversationId}
                                sources={message.sources}
                            />
                            {message.sources.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {message.sources.map((source) => (
                                        <MessageCitation
                                            key={`${source.kind}-${source.index}`}
                                            source={source}
                                            conversationId={message.conversationId}
                                            variant="chip"
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
        </div>
    )
}

export default MessageItem
