import { Pin } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import useCreateNoteResource from '@/hooks/useCreateNoteResource'
import { useResources } from '@/hooks/useResources'
import { chatNoteForMessage, chatNoteFromMessage } from '@/lib/note'
import { cn } from '@/lib/utils'
import type { Message } from '@/types/Message'

import MessageCitation from './messageCitation/MessageCitation'
import MarkdownContent from './MarkdownContent'

const MessageItem = ({ message }: { message: Message }) => {
    const isUser = message.role === 'user'
    const { conversationId, openStudioNote } = useConversationContext()
    const { data: resources } = useResources(conversationId)
    const { mutate } = useCreateNoteResource(conversationId)
    const existingNote = chatNoteForMessage(resources, message.id)

    const saveInNote = () => {
        if (existingNote) {
            openStudioNote(existingNote)
            return
        }
        mutate(
            { content: chatNoteFromMessage(message) },
            { onSuccess: ({ resource }) => openStudioNote(resource) },
        )
    }

    return (
        <div className={cn('flex w-full px-1 py-3 md:px-3', isUser ? 'justify-end font-semibold' : 'font-normal')}>
            {isUser
                ? <p className="max-w-[85%] break-all rounded-3xl bg-mist-300 px-4 py-3 md:max-w-2/3 md:px-5">{message.text}</p>
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
                                onClick={saveInNote}
                                variant="outline"
                                className="w-40 cursor-pointer"
                            >
                                <Pin />
                                {existingNote ? 'Open note' : 'Save in note'}
                            </Button>
                        </div>
                    )}
        </div>
    )
}

export default MessageItem
