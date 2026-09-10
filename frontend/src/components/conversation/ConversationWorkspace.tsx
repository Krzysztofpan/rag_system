import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { cn } from '@/lib/utils'

import ConversationWindow from './conversationView/ConversationWindow'
import SourceSection from './sources/SourceSection'
import StudioPanelSection from './studio/StudioPanelSection'
import ConversationMobileNav from './ConversationMobileNav'
import CustomSidebarProvider from './CustomSidebarProvider'

function ConversationWorkspace() {
    const { mobileSection } = useConversationContext()

    return (
        <div
            className={cn(
                'flex min-h-0 flex-1 flex-col',
                'max-md:overflow-hidden max-md:rounded-xl max-md:bg-background max-md:ring-1 max-md:ring-sidebar-border',
                'md:flex-row md:gap-4',
            )}
        >
            <ConversationMobileNav />
            <div
                className={cn(
                    'min-h-0 max-md:flex max-md:flex-1 max-md:flex-col',
                    mobileSection !== 'sources' && 'max-md:hidden',
                    'md:contents',
                )}
            >
                <CustomSidebarProvider>
                    <SourceSection />
                </CustomSidebarProvider>
            </div>
            <main
                className={cn(
                    'flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl ring-1 ring-sidebar-border',
                    'max-md:rounded-none max-md:ring-0',
                    mobileSection !== 'chat' && 'max-md:hidden',
                )}
            >
                <ConversationWindow />
            </main>
            <div
                className={cn(
                    'min-h-0 max-md:flex max-md:flex-1 max-md:flex-col',
                    mobileSection !== 'studio' && 'max-md:hidden',
                    'md:contents',
                )}
            >
                <CustomSidebarProvider>
                    <StudioPanelSection />
                </CustomSidebarProvider>
            </div>
        </div>
    )
}

export default ConversationWorkspace
