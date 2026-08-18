import { Separator } from '../ui/separator'
import InputMessage from './InputMessage'
import MessagesView from './MessagesView'

const ConversationWindow = ({ conversationId }: { conversationId: string }) => {
    return (
        <div className="flex h-full flex-col">
            <div className="shrink-0 p-3">Chat</div>
            <Separator />
            <div className="flex min-h-0 flex-1 flex-col p-5">
                <MessagesView key={conversationId} conversationId={conversationId} />
                <InputMessage />
            </div>
        </div>
    )
}

export default ConversationWindow
