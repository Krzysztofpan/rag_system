import { useMutation } from '@tanstack/react-query'

import { apiService } from '@/services/api/apiService'

import { useSourcesClient } from './useSources'

export const useEditSourceName = (conversationId: string) => {
    const { editSourceName } = useSourcesClient(conversationId)
    return useMutation({
        mutationFn: ({ documentId, name }: { documentId: string; name: string }) =>
            apiService.editSourceName(conversationId, documentId, name),
        onMutate: ({ documentId, name }) => {
            const previousName = editSourceName(documentId, name)

            return { previousName }
        },
        onError: (_err, { documentId }, context) => {
            if (context?.previousName == null) return
            editSourceName(documentId, context.previousName)
        },
    })
}
