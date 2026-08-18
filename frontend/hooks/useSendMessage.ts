
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { useConversationContext } from '@/contexts/conversation/ConversationContext';
import { apiService } from '@/services/api/apiService'
import type { Message } from '@/types/Message';

import { useInfiniteMessagesClient } from './useInfiniteMessages';

type useSendMessageFncProps = {
    documentIds: string[];
    message: string;
}

export const useSendMessage = (conversationId: string) => {
    const queryClient = useQueryClient()
    const { addNewMessage } = useInfiniteMessagesClient(queryClient, conversationId, 5)
    const { setIsPendingMessage } = useConversationContext()
    return useMutation({
        mutationFn: async ({ documentIds, message }: useSendMessageFncProps) => {
            const assistantMessage = await apiService.sendMessage(conversationId, documentIds, message)

            return assistantMessage
        },
        onMutate: ({ message }: useSendMessageFncProps) => {
            const messageObj: Message = { id: crypto.randomUUID(), conversationId: conversationId, role: 'user', text: message, createdAt: Date.now().toLocaleString() }
            addNewMessage(messageObj)
            setIsPendingMessage(true)
        },
        onSuccess: (data) => {
            addNewMessage(data.response)
        },
        onSettled: () => {
            setIsPendingMessage(false)
        },
    })
}
