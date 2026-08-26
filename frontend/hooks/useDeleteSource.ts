import { useMutation } from '@tanstack/react-query'

import { apiService } from '@/services/api/apiService'

import { useConversationsClient } from './useConversations'
import { useSourcesClient } from './useSources'

export const useDeleteSource = (conversationId: string) => {
    const sourcesClient = useSourcesClient(conversationId)
    const { bumpSourceCount } = useConversationsClient()
    return useMutation({
        mutationFn: (documentId: string) =>
            apiService.deleteSource(conversationId, documentId),
        onMutate: (documentId: string) => {
            const fallbackObj = sourcesClient.deleteSource(documentId)
            if (fallbackObj != null) {
                bumpSourceCount(conversationId, -1)
            }
            return fallbackObj
        },
        onError: (_err, _, fallbackObj) => {
            if (fallbackObj == null) return
            sourcesClient.insertSourceInIndex(fallbackObj)
            bumpSourceCount(conversationId, 1)
        },
    })
}
