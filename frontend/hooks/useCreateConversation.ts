import { useNavigate } from 'react-router'
import { useMutation } from '@tanstack/react-query'

import { toast } from '@/components/ui/toast'
import { apiErrorMessage } from '@/lib/apiError'
import { apiService } from '@/services/api/apiService'

import { useConversationsClient } from './useConversations'

const useCreateConveration = () => {
    const { addConversation } = useConversationsClient()

    const navigateTo = useNavigate()
    return useMutation({
        mutationFn: () =>
            apiService.createConversation(),
        onError: (error) => {
            toast.add({
                type: 'error',
                title: apiErrorMessage(error, 'Failed to create conversation'),
            })
        },
        onSuccess: (data) => {
            addConversation({
                id: data.conversationId,
                sourceCount: 0,
                title: 'New Conversation',
                topic: null,
                documentsSummary: null,
                userId: data.userId,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
            })
            void navigateTo(`/conversations/${data.conversationId}`)
        },
    })
}

export default useCreateConveration
