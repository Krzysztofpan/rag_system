import { isAxiosError } from 'axios'
import { ArrowLeftFromLine } from 'lucide-react'
import { Link, useParams } from 'react-router'

import ConversationWorkspace from '@/components/conversation/ConversationWorkspace'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import AvatarView from '@/components/utils/AvatarView'
import { ConversationProvider } from '@/contexts/conversation/ConversationProvider'
import { useConversation } from '@/hooks/useConversation'
import { getConversationTopicStyle } from '@/lib/conversationTopic'

const ConversationPage = () => {
    const { conversationId } = useParams<{ conversationId?: string }>()
    const { data: conversation, isLoading, error } = useConversation(conversationId)
    const { icon } = getConversationTopicStyle(conversation?.topic)
    if (!conversationId) {
        return <div>Conversation not found</div>
    }

    if (isAxiosError(error) && error.response?.status === 404) {
        return <div>Conversation not found</div>
    }

    if (isLoading && !conversation) {
        return null
    }

    return (
        <>
            <title>{`Folio - ${conversation?.title ?? 'New Conversation'}`}</title>
            <div className="flex h-svh flex-col gap-1 overflow-hidden px-3 pb-3 md:gap-2 md:px-5 md:pb-5">
                <header className="flex h-12 shrink-0 items-center gap-3 px-1 md:h-14 md:gap-4 md:px-2">
                    <Link to="/conversations" aria-label="Back to conversations" className="shrink-0">
                        <ArrowLeftFromLine />
                    </Link>
                    <h1 className="flex min-w-0 flex-1 items-center gap-2 text-lg font-medium md:text-xl">
                        <span className="shrink-0 leading-none" aria-hidden>
                            {icon}
                        </span>
                        <Tooltip>
                            <TooltipTrigger className="truncate" delay={200}>
                                <span>{conversation ? conversation.title : 'Default title'}</span>
                            </TooltipTrigger>
                            <TooltipContent>{conversation ? conversation.title : 'Default title'}</TooltipContent>
                        </Tooltip>
                    </h1>
                    <AvatarView />
                </header>
                <ConversationProvider>
                    <ConversationWorkspace />
                </ConversationProvider>
            </div>
        </>
    )
}

export default ConversationPage
