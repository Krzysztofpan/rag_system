import { createContext, type Dispatch, type SetStateAction, useContext } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';

import type { Source } from '@/types/source';

export type ConversationContextValue = {
    sourcesResponseObject: UseQueryResult<Source[]>;
    conversationId: string;
    unselectedSourcesIds: string[];
    setUnselectedSourcesIds: Dispatch<SetStateAction<string[]>>;
    selectedSources: string[];
    handleToogleSelectAllSources: (checked: boolean) => void;
    handleToogleSelectSource: (sourceId: string) => void;
}

export const ConversationContext = createContext<ConversationContextValue | null>(null)

export const useConversationContext = () => {
    const ctx = useContext(ConversationContext)
    if (!ctx) {
        throw new Error('useConversationContext must be used within AuthProvider')
    }
    return ctx
}
