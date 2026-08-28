import { useEffect, useState } from 'react'
import { Check, Copy } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useConversation } from '@/hooks/useConversation'

import MarkdownContent from './MarkdownContent'

const ConversationDocumentsOverview = () => {
    const { conversationId, sourcesResponseObject } = useConversationContext()
    const { data: conversation } = useConversation(conversationId)
    const { data: sources = [] } = sourcesResponseObject
    const [copied, setCopied] = useState(false)

    useEffect(() => {
        if (!copied) {
            return
        }
        const timeout = window.setTimeout(() => setCopied(false), 1500)
        return () => window.clearTimeout(timeout)
    }, [copied])

    const documentsSummary = conversation?.documentsSummary ?? null
    const sourceInFlight = sources.some(
        (source) => source.status === 'pending' || source.status === 'processing',
    )

    if (!documentsSummary && sourceInFlight) {
        return (
            <div className="flex flex-col gap-3 mt-10 pb-6">
                <Skeleton className="h-9 w-2/3" />
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-20 w-full" />
            </div>
        )
    }

    if (!conversation || !documentsSummary) {
        return null
    }

    const createdAt = new Date(conversation.createdAt).toLocaleDateString(undefined, {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
    })
    const sourceCount = sources.length
    const sourceLabel = sourceCount === 1 ? 'source' : 'sources'

    const copySummary = async () => {
        try {
            await navigator.clipboard.writeText(documentsSummary)
            setCopied(true)
        }
        catch {
            setCopied(false)
        }
    }

    return (
        <div className="flex flex-col gap-3 mt-10 pb-6">
            <h2 className="text-3xl font-semibold tracking-tight text-balance">
                {conversation.title}
            </h2>
            <p className="text-sm text-muted-foreground">
                {sourceCount}
                {' '}
                {sourceLabel}
                {' '}
                ·
                {' '}
                {createdAt}
            </p>
            <MarkdownContent
                content={documentsSummary}
                className="text-[0.95rem] leading-relaxed text-foreground"
            />
            <div className="flex items-center gap-1">
                <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => void copySummary()}
                    aria-label={copied ? 'Summary copied' : 'Copy summary'}
                >
                    {copied ? <Check /> : <Copy />}
                </Button>
            </div>
        </div>
    )
}

export default ConversationDocumentsOverview
