import { Search } from 'lucide-react'

import type { ToolInvocation } from '@/contexts/conversation/ConversationContext'

const TOOL_LABELS: Record<string, string> = {
    search_documents: 'Searching selected documents',
    summarize_context: 'Summarizing document context',
    web_search_tavily: 'Searching the web',
}

const ToolInvocationNotice = ({ invocation }: { invocation: ToolInvocation }) => (
    <div className="flex items-center gap-2 px-3 text-sm text-muted-foreground" role="status">
        <Search className="size-4" />
        <span>{TOOL_LABELS[invocation.name] ?? 'Using a tool'}</span>
    </div>
)

export default ToolInvocationNotice
