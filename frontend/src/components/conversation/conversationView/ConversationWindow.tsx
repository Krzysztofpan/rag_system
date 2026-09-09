import { useConversationContext } from '@/contexts/conversation/ConversationContext'

import InputMessage from './InputMessage'
import MessagesView from './MessagesView'

const ConversationWindow = () => {
    const { conversationId } = useConversationContext()

    return (
        <div className="flex h-full flex-col">
            <div className="flex min-h-0 flex-1 flex-col p-5">
                <MessagesView key={conversationId} conversationId={conversationId} />
                <InputMessage />
            </div>
        </div>
    )
}

export default ConversationWindow
