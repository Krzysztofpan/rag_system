import { useContext } from 'react'
import { useIsMutating, useMutation } from '@tanstack/react-query'

import { toast } from '@/components/ui/toast'
import { ConversationContext } from '@/contexts/conversation/ConversationContext'
import { apiErrorMessage } from '@/lib/apiError'
import { apiService } from '@/services/api/apiService'
import type { CreateNoteRequest } from '@/services/api/types'

import { useResourcesClient } from './useResources'


export const createNoteResourceMutationKey = (conversationId: string) =>
    ['createNoteResource', conversationId] as const

const useCreateNoteResource = (conversationId: string) => {
    const conversation = useContext(ConversationContext)
    const { addResource } = useResourcesClient(conversationId)
    const mutationKey = createNoteResourceMutationKey(conversationId)

    const mutation = useMutation({
        mutationKey,
        mutationFn: (body?: CreateNoteRequest) => {
            if (body?.content?.kind === 'chat') {
                conversation?.armConversationEvents()
            }
            return apiService.createNoteResource(conversationId, body)
        },

        onError: (error) => {
            toast.add({
                type: 'error',
                title: apiErrorMessage(error, 'Failed to create new note'),
            })
        },
        onSuccess: (data, body) => {
            addResource(data.resource)
            if (body?.content?.kind === 'chat') {
                conversation?.armConversationEvents(data.resource.id)
            }
        },
    })

    const isPending = useIsMutating({ mutationKey }) > 0

    return { ...mutation, isPending }
}

export default useCreateNoteResource
