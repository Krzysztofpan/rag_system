import { useIsMutating, useMutation } from '@tanstack/react-query'

import { toast } from '@/components/ui/toast'
import { apiErrorMessage } from '@/lib/apiError'
import { apiService } from '@/services/api/apiService'
import type { NoteContent } from '@/services/api/types'

import { useResourcesClient } from './useResources'


export const createNoteResourceMutationKey = (conversationId: string) =>
    ['createNoteResource', conversationId] as const

const useCreateNoteResource = (conversationId: string) => {
    const { addResource } = useResourcesClient(conversationId)
    const mutationKey = createNoteResourceMutationKey(conversationId)

    const mutation = useMutation({
        mutationKey,
        mutationFn: (body?: { title: string; content: NoteContent }) =>
            apiService.createNoteResource(conversationId, body),

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

    const isPending = useIsMutating({ mutationKey }) > 0

    return { ...mutation, isPending }
}

export default useCreateNoteResource
