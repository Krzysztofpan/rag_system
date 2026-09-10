import { type ConversationMobileSection, useConversationContext } from '@/contexts/conversation/ConversationContext'
import { cn } from '@/lib/utils'

const TABS: { id: ConversationMobileSection; label: string }[] = [
    { id: 'sources', label: 'Sources' },
    { id: 'chat', label: 'Chat' },
    { id: 'studio', label: 'Studio' },
]

function ConversationMobileNav() {
    const { mobileSection, setMobileSection } = useConversationContext()

    return (
        <nav
            className="grid shrink-0 grid-cols-3 border-b border-sidebar-border md:hidden"
            role="tablist"
            aria-label="Conversation sections"
        >
            {TABS.map((tab) => {
                const isActive = mobileSection === tab.id

                return (
                    <button
                        key={tab.id}
                        type="button"
                        role="tab"
                        aria-selected={isActive}
                        onClick={() => setMobileSection(tab.id)}
                        className={cn(
                            'relative cursor-pointer py-3 text-sm font-medium transition-colors',
                            isActive ? 'text-foreground' : 'text-muted-foreground',
                        )}
                    >
                        {tab.label}
                        {isActive && (
                            <span
                                aria-hidden
                                className="absolute bottom-0 left-1/2 h-0.5 w-8 -translate-x-1/2 rounded-full bg-sidebar-primary"
                            />
                        )}
                    </button>
                )
            })}
        </nav>
    )
}

export default ConversationMobileNav
