import { useMutation } from '@tanstack/react-query'

import { isOptimisticSourceId } from '@/lib/source'
import { apiService } from '@/services/api/apiService'

import { useConversationsClient } from './useConversations'
import { useSourcesClient } from './useSources'

export const useDeleteSource = (conversationId: string) => {
    const sourcesClient = useSourcesClient(conversationId)
    const { bumpSourceCount } = useConversationsClient()
    return useMutation({
        mutationFn: async (documentId: string) => {
            if (isOptimisticSourceId(documentId)) {
                return
            }
            await apiService.deleteSource(conversationId, documentId)
        },
        onMutate: async (documentId: string) => {
            const fallbackObj = await sourcesClient.deleteSource(documentId)
            if (fallbackObj != null && !isOptimisticSourceId(documentId)) {
                bumpSourceCount(conversationId, -1)
            }
            return fallbackObj
        },
        onError: (_err, documentId, fallbackObj) => {
            if (fallbackObj == null || isOptimisticSourceId(documentId)) return
            sourcesClient.insertSourceInIndex(fallbackObj)
            bumpSourceCount(conversationId, 1)
        },
    })
}
