import { useConversations } from '@/hooks/useConversations'

import { Card, CardContent } from '../ui/card'
import { Skeleton } from '../ui/skeleton'
import AddNewConversationBtn from './AddNewConversationBtn'
import ConversationCard from './ConversationCard'

function ConversationCardSkeleton() {
    return (
        <Card className="h-[240px] w-full">
            <CardContent className="flex h-full w-full flex-col justify-between">
                <div className="flex justify-between">
                    <Skeleton className="size-12 rounded" />
                    <Skeleton className="size-8 rounded" />
                </div>
                <div className="flex flex-col gap-2">
                    <Skeleton className="h-8 w-4/5" />
                    <Skeleton className="h-8 w-3/5" />
                    <Skeleton className="mt-1 h-4 w-2/3" />
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
        <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
            <AddNewConversationBtn />
            {!isLoading ? sortedConversations?.map((conversation) => <ConversationCard key={conversation.id} conversation={conversation} />) : Array.from({ length: 4 }).map((_, i) => <ConversationCardSkeleton key={i} />)}
            {error && (
                <Card className="h-[240px] w-full">
                    <CardContent className="flex h-full w-full items-center justify-center text-2xl text-destructive">
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
