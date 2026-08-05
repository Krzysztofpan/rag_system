import type { CSSProperties } from 'react'
import { useParams } from 'react-router'

import SourceSection from '@/components/Sources/SourceSection'
import { SidebarProvider } from '@/components/ui/sidebar'

const ConversationPage = () => {
    const { conversationId } = useParams<{ conversationId: string }>()

    return (
        <SidebarProvider
            className="flex h-svh flex-col overflow-hidden"
            style={
                {
                    '--sidebar-width': '25vw',
                } as CSSProperties
            }
        >
            <header className="flex h-14 shrink-0 items-center px-4">
                <h1 className="text-lg font-medium">AI Assistant</h1>
            </header>
            <div className="flex min-h-0 flex-1 gap-2 p-2 pt-0">
                <SourceSection conversationId={conversationId} />
                <main className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto rounded-xl ring-1 ring-sidebar-border">
                    <div>main</div>
                </main>
            </div>
        </SidebarProvider>
    );
}

export default ConversationPage;
