import { useAuthQuery } from '@/hooks/useAuthQuery'
import { apiService } from '@/services/api/apiService'
import type { Conversation } from '@/types/conversation'

export const useConversations = () => {
    return useAuthQuery({
        queryKey: ['conversations'],
        queryFn: async (): Promise<Conversation[]> => {
            const response = await apiService.getConversations()

            return response.conversations
        },
    })
}
