import { Pin } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import useCreateNoteResource from '@/hooks/useCreateNoteResource'
import { cn } from '@/lib/utils'
import type { Message } from '@/types/Message'

import MessageCitation from './messageCitation/MessageCitation'
import MarkdownContent from './MarkdownContent'

const MessageItem = ({ message }: { message: Message }) => {
    const isUser = message.role === 'user'
    const { conversationId } = useConversationContext()
    const { mutate } = useCreateNoteResource(conversationId)
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
                            <Button
                                onClick={() => mutate({
                                    title: '',
                                    content: {
                                        kind: 'chat',
                                        markdown: message.text,
                                        messageId: message.id,
                                        sources: message.sources,
                                    },
                                })}
                                variant="outline"
                                className="w-40 cursor-pointer"
                            >
                                <Pin />
                                Save in note
                            </Button>
                        </div>
                    )}
        </div>
    )
}

export default MessageItem
