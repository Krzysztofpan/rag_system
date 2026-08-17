import { cn } from '@/lib/utils'
import type { Message } from '@/types/Message'

import MarkdownContent from './MarkdownContent'

const MessageItem = ({ message }: { message: Message }) => {
    const isUser = message.role === 'user'

    return (
        <div className={cn('flex w-full px-3 py-3', isUser ? 'justify-end font-semibold' : 'font-normal')}>
            {isUser
                ? <p className="max-w-2/3 break-all rounded-3xl bg-mist-300 px-5 py-3">{message.text}</p>
                : <MarkdownContent content={message.text} className="max-w-full" />}
        </div>
    )
}

export default MessageItem
