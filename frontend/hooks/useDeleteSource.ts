import { useMutation } from '@tanstack/react-query'

import { apiService } from '@/services/api/apiService'

import { useSourcesClient } from './useSources'

export const useDeleteSource = (conversationId: string) => {
    const sourcesClient = useSourcesClient(conversationId)
    return useMutation({
        mutationFn: (documentId: string) =>
            apiService.deleteSource(conversationId, documentId),
        onMutate: (documentId: string) => {
            sourcesClient.deleteSource(documentId)
        },
    })
}
