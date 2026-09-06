import { apiService } from '@/services/api/apiService'
import type { GetResourcesResponse } from '@/services/api/types'

import { useAuthQuery } from './useAuthQuery'

export const useResources = (conversationId: string | null) => {
    return useAuthQuery({
        queryKey: ['conversation-resources', conversationId],
        queryFn: async (): Promise<GetResourcesResponse> => {
            if (!conversationId) {
                throw new Error('Conversation id is required')
            }
            return apiService.getResources(conversationId)
        },
        enabled: !!conversationId,
    })
}
