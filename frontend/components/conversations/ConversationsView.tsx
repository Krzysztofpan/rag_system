import { useConversations } from '@/hooks/useConversations'

import { Card, CardContent } from '../ui/card'
import { Skeleton } from '../ui/skeleton'
import AddNewConversationBtn from './AddNewConversationBtn'
import ConversationCard from './ConversationCard'

function ConversationCardSkeleton() {
    return (
        <Card className="max-w-[320px]">
            <CardContent className="w-full flex flex-col gap-10">
                <div className="flex justify-between">
                    <Skeleton className="size-20 rounded" />
                    <Skeleton className="size-8 rounded" />
                </div>
                <div className="flex flex-col gap-2">
                    <Skeleton className="h-8 w-4/5" />
                    <Skeleton className="h-8 w-3/5" />
                    <Skeleton className="h-4 w-2/3 mt-1" />
                </div>
            </CardContent>
        </Card>
    )
}

const ConversationsView = () => {
    const { data: conversations = [], isLoading, error } = useConversations()

    const sortedConversations = conversations.toSorted(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    )

    return (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4 w-full">
            <AddNewConversationBtn />
            {!isLoading ? sortedConversations?.map((conversation) => <ConversationCard key={conversation.id} conversation={conversation} />) : Array.from({ length: 4 }).map((_, i) => <ConversationCardSkeleton key={i} />)}
            {error && (
                <Card className="max-w-[320px] h-[250px]">
                    <CardContent className="w-full flex justify-center h-full items-center text-destructive  text-2xl">
                        <h1 className="text-center">
                            Failed To load Conversations
                        </h1>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}

export default ConversationsView
