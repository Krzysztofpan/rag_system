import { createContext, type Dispatch, type SetStateAction, useContext } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'

import type { Message } from '@/types/Message'
import type { Source } from '@/types/source'

export type ToolInvocation = {
    id: string;
    name: string;
}

export type ConversationContextValue = {
    sourcesResponseObject: UseQueryResult<Source[]>;
    conversationId: string;
    unselectedSourcesIds: string[];
    setUnselectedSourcesIds: Dispatch<SetStateAction<string[]>>;
    selectedSources: string[];
    handleToogleSelectAllSources: (checked: boolean) => void;
    handleToogleSelectSource: (sourceId: string) => void;
    isPendingMessage: boolean;
    sendMessage: (input: { documentIds: string[]; message: string }) => Promise<void>;
    streamedMessage: Message | null;
    streamError: string | null;
    toolInvocations: ToolInvocation[];
}

export const ConversationContext = createContext<ConversationContextValue | null>(null)

export const useConversationContext = () => {
    const ctx = useContext(ConversationContext)
    if (!ctx) {
        throw new Error('useConversationContext must be used within AuthProvider')
    }
    return ctx
}
