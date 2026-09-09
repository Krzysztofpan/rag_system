import { useMutation } from '@tanstack/react-query'

import { apiService } from '@/services/api/apiService'

import { useConversationsClient } from './useConversations'

export const useEditConversationTitle = () => {
    const { editConversationTitle } = useConversationsClient()
    return useMutation({
        mutationFn: ({ conversationId, title }: { conversationId: string; title: string }) =>
            apiService.eidtConversationTitle(conversationId, title),
        onMutate: ({ conversationId, title }) => {
            const previousName = editConversationTitle(conversationId, title)
            return { previousName }
        },
        onError: (_err, { conversationId }, context) => {
            if (context?.previousName == null) return
            editConversationTitle(conversationId, context.previousName)
        },
    })
}
