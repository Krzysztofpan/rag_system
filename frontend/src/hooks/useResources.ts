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

    const updateResource = (resource: Resource) => {
        queryClient.setQueryData<Resource[]>(queryKey, (current = []) =>
            current.map((item) => (item.id === resource.id ? resource : item)),
        )
    }

    const deleteResource = async (resourceId: string) => {
        await queryClient.cancelQueries({ queryKey })
        let fallbackObj

        queryClient.setQueryData<Resource[]>(queryKey, (current = []) =>
            current.filter((resource, i) => {
                if (resource.id !== resourceId) {
                    return true
                }

                fallbackObj = { deletedResource: resource, index: i }
                return false
            }),
        )

        return fallbackObj
    }

    const insertResourceInIndex = (fallbackObj: { deletedResource: Resource; index: number }) => {
        queryClient.setQueryData<Resource[]>(queryKey, (current = []) => {
            const next = [...current]
            const clampedIndex = Math.max(0, Math.min(fallbackObj.index, next.length))
            next.splice(clampedIndex, 0, fallbackObj.deletedResource)
            return next
        })
    }

    return {
        addResource,
        updateResource,
        deleteResource,
        insertResourceInIndex,
    }
}
