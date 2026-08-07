

import { useConversations } from '@/hooks/useConversations';

import AddNewConversationBtn from './AddNewConversationBtn';
import ConversationCard from './ConversationCard';

const ConversationsView = () => {
    const { data: conversations = [], isLoading } = useConversations()

    if (isLoading) return null

    return (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4 w-full">
            <AddNewConversationBtn />
            {conversations?.map((conversation) => (
                <ConversationCard key={conversation.id} conversation={conversation} />
            ))}
        </div>
    );
}

export default ConversationsView;
