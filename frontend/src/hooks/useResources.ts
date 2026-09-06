import { useQueryClient } from '@tanstack/react-query'

import { apiService } from '@/services/api/apiService'
import type { Resource } from '@/services/api/types'

import { useAuthQuery } from './useAuthQuery'
import { useUserQueryKey } from './useUserQueryKey'

export const useResources = (conversationId: string | null) => {
    return useAuthQuery({
        queryKey: ['conversation-resources', conversationId],
        queryFn: async (): Promise<Resource[]> => {
            if (!conversationId) {
                throw new Error('Conversation id is required')
            }
            const response = await apiService.getResources(conversationId)
            return response.conversationResources
        },
        enabled: !!conversationId,
    })
}


export const useResourcesClient = (conversationId: string) => {
    const queryClient = useQueryClient()
    const queryKey = useUserQueryKey('conversation-resources', conversationId)

    const addResource = (resource: Resource) => {
        queryClient.setQueryData<Resource[]>(queryKey, (current = []) =>
            [...current, resource],
        )
    }

    return {
        addResource,
    }
}
