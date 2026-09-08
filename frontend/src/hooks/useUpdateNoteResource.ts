import { useMutation } from '@tanstack/react-query'

import { toast } from '@/components/ui/toast'
import { apiErrorMessage } from '@/lib/apiError'
import { apiService } from '@/services/api/apiService'
import type { UpdateNoteRequest } from '@/services/api/types'

import { useResourcesClient } from './useResources'


const useUpdateNoteResource = (conversationId: string) => {
    const { updateResource } = useResourcesClient(conversationId)

    return useMutation({
        mutationFn: ({ resourceId, ...body }: { resourceId: string } & UpdateNoteRequest) =>
            apiService.updateNoteResource(conversationId, resourceId, body),

        onError: (error) => {
            toast.add({
                type: 'error',
                title: apiErrorMessage(error, 'Failed to save note'),
            })
        },
        onSuccess: (data) => {
            updateResource(data.resource)
        },
    })
}

export default useUpdateNoteResource
