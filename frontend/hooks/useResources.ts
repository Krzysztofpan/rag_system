import { useQuery, useQueryClient } from '@tanstack/react-query'

import { applyUploadResponse, createPendingResource, rejectResource } from '@/lib/resource'
import { apiService } from '@/services/api/apiService'
import type { Resource } from '@/types/resource'

export const resourcesQueryKey = (conversationId: string) =>
    ['conversation-resources', conversationId] as const

export const useResources = (conversationId: string) => {
    return useQuery<Resource[]>({
        queryKey: resourcesQueryKey(conversationId),
        queryFn: async (): Promise<Resource[]> => {
            const response = await apiService.getResources(conversationId)
            return response.conversationResources
        },
    })
}

export const useResourcesClient = (conversationId: string) => {
    const queryClient = useQueryClient()
    const queryKey = resourcesQueryKey(conversationId)

    const addResource = (resource: Resource) => {
        queryClient.setQueryData<Resource[]>(queryKey, (current = []) => [
            ...current,
            resource,
        ])
    }

    const replaceResource = (resourceId: string, nextResource: Resource) => {
        queryClient.setQueryData<Resource[]>(queryKey, (current = []) =>
            current.map((resource) =>
                resource.id === resourceId ? nextResource : resource,
            ),
        )
    }

    const uploadResource = async (file: File) => {
        const pendingResource = createPendingResource(file)
        addResource(pendingResource)

        try {
            const formData = new FormData()
            formData.append('file', file)
            const body = await apiService.uploadResource(conversationId, formData)
            replaceResource(pendingResource.id, applyUploadResponse(pendingResource, body))
        }
        catch {
            replaceResource(
                pendingResource.id,
                rejectResource(pendingResource, 'Server didn\'t respond'),
            )
        }
    }

    return {
        addResource,
        replaceResource,
        uploadResource,
    }
}
