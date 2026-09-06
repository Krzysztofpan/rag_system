
import { useMutation } from '@tanstack/react-query'

import { toast } from '@/components/ui/toast'
import { apiErrorMessage } from '@/lib/apiError'
import { apiService } from '@/services/api/apiService'

import { useResourcesClient } from './useResources'


const useCreateNoteResource = (conversationId: string) => {
    const { addResource } = useResourcesClient(conversationId)

    return useMutation({
        mutationFn: () =>
            apiService.createNoteResource(conversationId),

        onError: (error) => {
            toast.add({
                type: 'error',
                title: apiErrorMessage(error, 'Failed to create new note'),
            })
        },
        onSuccess: (data) => {
            addResource(data.resource)
        },
    })
}

export default useCreateNoteResource
