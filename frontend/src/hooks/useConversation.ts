import { useQueryClient } from '@tanstack/react-query'

import { useAuthQuery } from '@/hooks/useAuthQuery'
import { useUserQueryKey } from '@/hooks/useUserQueryKey'
import { apiService } from '@/services/api/apiService'
import type { Conversation } from '@/types/conversation'

export const useConversation = (conversationId: string | undefined) => {
    const queryClient = useQueryClient()
    const listQueryKey = useUserQueryKey('conversations')

    return useAuthQuery({
        queryKey: ['conversations', conversationId],
        queryFn: () => apiService.getConversation(conversationId as string),
        enabled: !!conversationId,
        placeholderData: () =>
            queryClient
                .getQueryData<Conversation[]>(listQueryKey)
                ?.find((conversation) => conversation.id === conversationId),
    })
}
