import { useNavigate } from 'react-router'
import { useMutation } from '@tanstack/react-query'

import { apiService } from '@/services/api/apiService'

import { useConversationsClient } from './useConversations'

const useCreateConveration = () => {
    const { addConversation } = useConversationsClient()

    const navigateTo = useNavigate()
    return useMutation({
        mutationFn: () =>
            apiService.createConversation(),
        onSuccess: (data) => {
            addConversation({
                id: data.conversationId,
                sourceCount: 0,
                title: 'New Conversation',
                topic: null,
                userId: data.userId,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
            })
            void navigateTo(`/conversations/${data.conversationId}`)
        },
    })
}

export default useCreateConveration
