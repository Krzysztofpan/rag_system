
import { Separator } from '../ui/separator';
import InputMessage from './InputMessage';
import MessagesView from './MessagesView';

const ConversationWindow = () => {
    return (
        <div className="flex flex-col h-full">
            <div className="p-3">
                Chat
            </div>
            <Separator />
            <div className="flex flex-col h-full p-5">
                <MessagesView />
                <InputMessage />
            </div>
        </div>
    );
}

export default ConversationWindow;
