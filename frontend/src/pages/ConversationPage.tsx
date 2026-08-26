import { isAxiosError } from 'axios'
import { ArrowLeftFromLine } from 'lucide-react'
import type { CSSProperties } from 'react'
import { Link, useParams } from 'react-router'

import ConversationWindow from '@/components/conversationView/ConversationWindow'
import SourceSection from '@/components/sources/SourceSection'
import { SidebarProvider } from '@/components/ui/sidebar'
import { ConversationProvider } from '@/contexts/conversation/ConversationProvider'
import { useConversation } from '@/hooks/useConversations'

const ConversationPage = () => {
    const { conversationId } = useParams<{ conversationId?: string }>()
    const { data: conversation, isLoading, error } = useConversation(conversationId)

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
        <SidebarProvider
            className="flex gap-2 h-svh flex-col overflow-hidden px-5"
            style={
                {
                    '--sidebar-width': '25vw',
                } as CSSProperties
            }
        >
            <header className="flex h-14 shrink-0 items-center px-4 gap-4">
                <Link to="/conversations">
                    <ArrowLeftFromLine />
                </Link>
                <h1 className="text-xl font-medium">{conversation ? conversation.title : 'Default title'}</h1>
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
    )
}

export default ConversationPage
