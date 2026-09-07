import { useMutation } from '@tanstack/react-query'

import { toast } from '@/components/ui/toast'
import { apiErrorMessage } from '@/lib/apiError'
import { apiService } from '@/services/api/apiService'

import { useResourcesClient } from './useResources'

export const useDeleteResource = (conversationId: string) => {
    const resourcesClient = useResourcesClient(conversationId)

    return useMutation({
        mutationFn: (resourceId: string) =>
            apiService.deleteResource(conversationId, resourceId),
        onMutate: async (resourceId: string) => {
            return await resourcesClient.deleteResource(resourceId)
        },
        onError: (error, _resourceId, fallbackObj) => {
            if (fallbackObj != null) {
                resourcesClient.insertResourceInIndex(fallbackObj)
            }
            toast.add({
                type: 'error',
                title: apiErrorMessage(error, 'Failed to delete resource'),
            })
        },
    })
}
