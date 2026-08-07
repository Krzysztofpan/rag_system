import { useQueryClient } from '@tanstack/react-query'

import { useAuthQuery } from '@/hooks/useAuthQuery'
import { apiService } from '@/services/api/apiService'
import type { Conversation } from '@/types/conversation'

import { useUserQueryKey } from './useUserQueryKey'

export const useConversations = () => {
    return useAuthQuery({
        queryKey: ['conversations'],
        queryFn: async (): Promise<Conversation[]> => {
            const response = await apiService.getConversations()

            return response.conversations
        },
    })
}

export const useConversationsClient = () => {
    const queryClient = useQueryClient()
    const queryKey = useUserQueryKey('conversations')

    const addConversation = (conversation: Conversation) => {
        queryClient.setQueryData<Conversation[]>(queryKey, (current = []) => [...current, conversation])
    }

    const deleteConversation = (conversationId: string) => {
        let fallbackObj

        queryClient.setQueryData<Conversation[]>(queryKey, (current = []) =>
            current.filter((conversation, i) => {
                if (conversation.id !== conversationId) {
                    return true
                }

                fallbackObj = { deletedConversation: conversation, index: i }
                return false
            }),
        )

        return fallbackObj
    }

    const editConversationTitle = (conversationId: string, updatedTitle: string) => {
        let previousName: string | null

        queryClient.setQueryData<Conversation[]>(queryKey, (current = []) =>
            current.map((conversation) => {
                if (conversation.id !== conversationId) return conversation
                previousName = conversation.conversationTitle
                return { ...conversation, conversationTitle: updatedTitle }
            }),
        )

        return previousName
    }

    const insertConversationInIndex = (fallbackObj: { deletedConversation: Conversation; index: number }) => {
        queryClient.setQueryData<Conversation[]>(queryKey, (current = []) => {
            const next = [...current]
            const clampedIndex = Math.max(0, Math.min(fallbackObj.index, next.length))
            next.splice(clampedIndex, 0, fallbackObj.deletedConversation)
            return next
        })
    }

    return {
        addConversation,
        deleteConversation,
        editConversationTitle,
        insertConversationInIndex,
    }
}
