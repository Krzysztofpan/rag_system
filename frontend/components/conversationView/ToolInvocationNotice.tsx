import { Search } from 'lucide-react'

import type { ToolInvocation } from '@/contexts/conversation/ConversationContext'

const TOOL_LABELS: Record<string, string> = {
    search_documents: 'Przeszukuję wybrane dokumenty',
    summarize_context: 'Podsumowuję kontekst dokumentów',
}

const ToolInvocationNotice = ({ invocation }: { invocation: ToolInvocation }) => (
    <div className="flex items-center gap-2 px-3 text-sm text-muted-foreground" role="status">
        <Search className="size-4" />
        <span>{TOOL_LABELS[invocation.name] ?? 'Korzystam z narzędzia'}</span>
    </div>
)

export default ToolInvocationNotice
