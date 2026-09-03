import { type CSSProperties, useState } from 'react'
import { isAxiosError } from 'axios'
import { ArrowLeftFromLine } from 'lucide-react'
import { Link, useParams } from 'react-router'

import ConversationWindow from '@/components/conversation/conversationView/ConversationWindow'
import SourceSection from '@/components/conversation/sources/SourceSection'
import { SidebarProvider } from '@/components/ui/sidebar'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import AvatarView from '@/components/utils/AvatarView'
import { ConversationProvider } from '@/contexts/conversation/ConversationProvider'
import { useIsMobile } from '@/hooks/use-mobile'
import { useConversation } from '@/hooks/useConversation'
import { getConversationTopicStyle } from '@/lib/conversationTopic'

const ConversationPage = () => {
    const { conversationId } = useParams<{ conversationId?: string }>()
    const { data: conversation, isLoading, error } = useConversation(conversationId)
    const { icon } = getConversationTopicStyle(conversation?.topic)
    const isMobile = useIsMobile()
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
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
            <SidebarProvider
                className="flex gap-2 h-svh flex-col overflow-hidden px-5"
                style={
                    {
                        '--sidebar-width': '25vw',
                    } as CSSProperties
                }
                open={!isMobile && isSidebarOpen}
                onOpenChange={setIsSidebarOpen}
            >
                <header className="flex h-14 shrink-0 items-center px-4 gap-4">
                    <Link to="/conversations">
                        <ArrowLeftFromLine />
                    </Link>
                    <h1 className="flex min-w-0 items-center gap-2 text-xl font-medium flex-1">
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
                    <div className="flex min-h-0 flex-1 gap-2 pt-0 mb-5">
                        <SourceSection />
                        <main className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden rounded-xl ring-1 ring-sidebar-border">
                            <ConversationWindow />
                        </main>
                    </div>
                </ConversationProvider>
            </SidebarProvider>
        </>
    )
}

export default ConversationPage
