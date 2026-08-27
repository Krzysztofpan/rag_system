import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { useAuthQuery } from '@/hooks/useAuthQuery'
import { userQueryKey } from '@/lib/queryKeys'
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
    const userId = queryKey[0]

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

    const editConversationTitle = useCallback((conversationId: string, updatedTitle: string) => {
        const listQueryKey = userQueryKey(userId, 'conversations')
        let previousName: string | null = null

        queryClient.setQueryData<Conversation[]>(listQueryKey, (current = []) =>
            current.map((conversation) => {
                if (conversation.id !== conversationId) return conversation
                previousName = conversation.title
                return { ...conversation, title: updatedTitle, updatedAt: new Date().toISOString() }
            }),
        )

        queryClient.setQueryData<Conversation>([...listQueryKey, conversationId], (current) => {
            if (!current) return current
            previousName ??= current.title
            return { ...current, title: updatedTitle }
        })

        return previousName
    }, [queryClient, userId])

    const patchConversation = useCallback((
        conversationId: string,
        patch: Partial<Pick<Conversation, 'title' | 'updatedAt' | 'sourceCount' | 'topic'>>,
    ) => {
        const listQueryKey = userQueryKey(userId, 'conversations')
        queryClient.setQueryData<Conversation[]>(listQueryKey, (current = []) =>
            current.map((conversation) => {
                if (conversation.id !== conversationId) return conversation

                return { ...conversation, ...patch }
            }),
        )
        queryClient.setQueryData<Conversation>([...listQueryKey, conversationId], (current) => {
            if (!current) return current
            return { ...current, ...patch }
        })
    }, [queryClient, userId])

    const markConversationUpdated = (conversationId: string) => {
        patchConversation(conversationId, { updatedAt: new Date().toISOString() })
    }

    const bumpSourceCount = (conversationId: string, delta: number) => {
        queryClient.setQueryData<Conversation[]>(queryKey, (current = []) =>
            current.map((conversation) => {
                if (conversation.id !== conversationId) return conversation

                return {
                    ...conversation,
                    sourceCount: Math.max(0, conversation.sourceCount + delta),
                    updatedAt: new Date().toISOString(),
                }
            }),
        )
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
        patchConversation,
        insertConversationInIndex,
        bumpSourceCount,
        markConversationUpdated,
    }
}
