import { type ReactNode, useState } from 'react';
import { useParams } from 'react-router';

import { useSources } from '@/hooks/useSources';

import { ConversationContext, type ConversationContextValue } from './ConversationContext';

export function ConversationProvider({ children }: { children: ReactNode }) {
    const { conversationId } = useParams<{ conversationId?: string }>()

    if (!conversationId) {
        throw new Error('ConversationProvider only can be used in Conversation route')
    }

    const sourcesResponseObject = useSources(conversationId)
    const { data: sources = [] } = sourcesResponseObject
    const [unselectedSourcesIds, setUnselectedSourcesIds] = useState<string[]>([])

    const selectedSources = sources.map((source) => source.id).filter((id) => !unselectedSourcesIds.includes(id))

    const handleToogleSelectAllSources = (checked: boolean) => {
        if (checked) {
            setUnselectedSourcesIds([])
            return
        }

        setUnselectedSourcesIds(sources.map((source) => source.id))
    }

    const handleToogleSelectSource = (sourceId: string) => {
        setUnselectedSourcesIds((prev) => (prev.includes(sourceId) ? prev.filter((id) => id !== sourceId) : [...prev, sourceId]))
    }

    const conversationContextObj: ConversationContextValue = {
        conversationId,
        handleToogleSelectAllSources,
        handleToogleSelectSource,
        selectedSources,
        setUnselectedSourcesIds,
        sourcesResponseObject,
        unselectedSourcesIds,
    }

    return <ConversationContext.Provider value={conversationContextObj}>{children}</ConversationContext.Provider>
}
