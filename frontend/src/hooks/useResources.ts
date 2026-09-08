import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { userQueryKey } from '@/lib/queryKeys'
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
    const userId = queryKey[0]

    const addResource = (resource: Resource) => {
        const pendingTitlesKey = userQueryKey(userId, 'pending-resource-titles', conversationId)
        const pending = queryClient.getQueryData<Record<string, string>>(pendingTitlesKey) ?? {}
        const title = pending[resource.id] ?? resource.title
        if (pending[resource.id] !== undefined) {
            const rest = Object.fromEntries(
                Object.entries(pending).filter(([id]) => id !== resource.id),
            )
            queryClient.setQueryData(pendingTitlesKey, rest)
        }
        queryClient.setQueryData<Resource[]>(queryKey, (current = []) =>
            [...current, { ...resource, title }],
        )
    }

    const updateResource = (resource: Resource) => {
        queryClient.setQueryData<Resource[]>(queryKey, (current = []) =>
            current.map((item) => (item.id === resource.id ? resource : item)),
        )
    }

    const patchResourceTitle = useCallback((resourceId: string, title: string) => {
        const listQueryKey = userQueryKey(userId, 'conversation-resources', conversationId)
        const pendingTitlesKey = userQueryKey(userId, 'pending-resource-titles', conversationId)
        queryClient.setQueryData<Resource[]>(listQueryKey, (current = []) => {
            if (!current.some((resource) => resource.id === resourceId)) {
                const pending = queryClient.getQueryData<Record<string, string>>(pendingTitlesKey) ?? {}
                queryClient.setQueryData(pendingTitlesKey, { ...pending, [resourceId]: title })
                return current
            }
            return current.map((item) => (
                item.id === resourceId ? { ...item, title } : item
            ))
        })
    }, [conversationId, queryClient, userId])

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
        patchResourceTitle,
        deleteResource,
        insertResourceInIndex,
    }
}
