import { useMutation } from '@tanstack/react-query';

import { apiService } from '@/services/api/apiService';

import { useConversationsClient } from './useConversations';

const useDeleteConversation = () => {
    const conversationsClient = useConversationsClient()

    return useMutation({
        mutationFn: (conversationId: string) =>
            apiService.deleteConversation(conversationId),
        onMutate: (conversationId: string) => {
            const fallbackObj = conversationsClient.deleteConversation(conversationId)
            return fallbackObj
        },
        onError: (_err, _, fallbackObj) => {
            if (fallbackObj == null) return
            conversationsClient.insertConversationInIndex(fallbackObj)
        },
    })
}

export default useDeleteConversation;
