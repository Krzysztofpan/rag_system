import { useContext } from 'react'
import { isAxiosError } from 'axios'
import { useQueryClient } from '@tanstack/react-query'

import { ConversationContext } from '@/contexts/conversation/ConversationContext'
import { useAuthQuery } from '@/hooks/useAuthQuery'
import { useConversationsClient } from '@/hooks/useConversations'
import { useUserQueryKey } from '@/hooks/useUserQueryKey'
import { createPendingSource, rejectSource } from '@/lib/source'
import { apiService } from '@/services/api/apiService'
import type { Source } from '@/types/source'

function sourceRequestError(error: unknown): string {
    if (!isAxiosError(error)) {
        return 'Server didn\'t respond'
    }
    const payload: unknown = error.response?.data
    if (typeof payload !== 'object' || payload === null) {
        return 'Server didn\'t respond'
    }
    const detail: unknown = Reflect.get(payload, 'detail')
    return typeof detail === 'string' ? detail : 'Server didn\'t respond'
}

export const useSources = (conversationId: string | null) => {
    return useAuthQuery({
        queryKey: ['conversation-sources', conversationId],
        queryFn: async (): Promise<Source[]> => {
            const response = await apiService.getSources(conversationId as string)
            return response.conversationSources
        },
        enabled: !!conversationId,
        refetchInterval: (query) => {
            const sources = query.state.data
            return sources?.some((source) => source.status === 'pending' || source.status === 'processing')
                ? 2000
                : false
        },
    })
}

export const useSourcesClient = (conversationId: string) => {
    const queryClient = useQueryClient()
    const queryKey = useUserQueryKey('conversation-sources', conversationId)
    const { bumpSourceCount } = useConversationsClient()
    const conversation = useContext(ConversationContext)

    const addSource = (source: Source) => {
        queryClient.setQueryData<Source[]>(queryKey, (current = []) => [...current, source])
    }

    const deleteSource = (sourceId: string) => {
        let fallbackObj

        queryClient.setQueryData<Source[]>(queryKey, (current = []) =>
            current.filter((source, i) => {
                if (source.id !== sourceId) {
                    return true
                }

                fallbackObj = { deletedSource: source, index: i }
                return false
            }),
        )

        return fallbackObj
    }

    const insertSourceInIndex = (fallbackObj: { deletedSource: Source; index: number }) => {
        queryClient.setQueryData<Source[]>(queryKey, (current = []) => {
            const next = [...current]
            const clampedIndex = Math.max(0, Math.min(fallbackObj.index, next.length))
            next.splice(clampedIndex, 0, fallbackObj.deletedSource)
            return next
        })
    }

    const replaceSource = (sourceId: string, nextSource: Source) => {
        queryClient.setQueryData<Source[]>(queryKey, (current = []) => current.map((source) => (source.id === sourceId ? nextSource : source)))
    }

    const addUrlSource = async (url: string) => {
        conversation?.armConversationEvents()
        const pendingSource = createPendingSource(url, 'video/youtube')
        addSource(pendingSource)

        try {
            const source = await apiService.addUrlSource(conversationId, url)
            replaceSource(pendingSource.id, source)
            bumpSourceCount(conversationId, 1)
        }
        catch (error) {
            replaceSource(pendingSource.id, rejectSource(pendingSource, sourceRequestError(error)))
        }
    }

    const uploadSource = async (file: File) => {
        conversation?.armConversationEvents()
        const pendingSource = createPendingSource(file.name, file.type || null)
        addSource(pendingSource)

        try {
            const formData = new FormData()
            formData.append('file', file)
            const source = await apiService.uploadSource(conversationId, formData)
            replaceSource(pendingSource.id, source)
            bumpSourceCount(conversationId, 1)
        }
        catch (error) {
            replaceSource(pendingSource.id, rejectSource(pendingSource, sourceRequestError(error)))
        }
    }

    const editSourceName = (sourceId: string, updatedName: string) => {
        let previousName: string | undefined

        queryClient.setQueryData<Source[]>(queryKey, (current = []) =>
            current.map((source) => {
                if (source.id !== sourceId) return source
                previousName = source.filename
                return { ...source, filename: updatedName }
            }),
        )

        return previousName
    }

    return {
        addSource,
        deleteSource,
        insertSourceInIndex,
        replaceSource,
        addUrlSource,
        uploadSource,
        editSourceName,
    }
}
