import { HttpAgentServerAdapter } from '@langchain/react'

import { apiService } from '@/services/api/apiService'

export const chatStreamPaths = {
    commands: (id: string) => `/conversations/${id}/commands`,
    stream: (id: string) => `/conversations/${id}/stream`,
    state: (id: string) => `/conversations/${id}/state`,
}

export function createChatStreamAdapter(conversationId: string) {
    return new HttpAgentServerAdapter({
        apiUrl: apiService.getApiHost(),
        threadId: conversationId,
        fetch: apiService.authorizedFetch,
        paths: chatStreamPaths,
    })
}
