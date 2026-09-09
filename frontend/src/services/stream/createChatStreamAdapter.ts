import { HttpAgentServerAdapter } from '@langchain/react'

import { rejectOnApiError } from '@/lib/apiError'
import { apiService } from '@/services/api/apiService'

export function chatStreamPaths(conversationId: string) {
    return {
        commands: `/conversations/${conversationId}/commands`,
        stream: `/conversations/${conversationId}/stream`,
        state: `/conversations/${conversationId}/state`,
    }
}

export function createChatStreamAdapter(conversationId: string) {
    return new HttpAgentServerAdapter({
        apiUrl: apiService.getApiHost(),
        threadId: conversationId,
        fetch: async (input, init) => rejectOnApiError(await apiService.authorizedFetch(input, init)),
        paths: chatStreamPaths(conversationId),
    })
}
