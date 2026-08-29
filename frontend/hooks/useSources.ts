import { useContext } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { toast } from '@/components/ui/toast'
import { ConversationContext } from '@/contexts/conversation/ConversationContext'
import { useAuthQuery } from '@/hooks/useAuthQuery'
import { useConversationsClient } from '@/hooks/useConversations'
import { useUserQueryKey } from '@/hooks/useUserQueryKey'
import { apiErrorMessage, isLimitError } from '@/lib/apiError'
import { createPendingSource, mergeFetchedSources, rejectSource, replaceSourceInList } from '@/lib/source'
import { apiService } from '@/services/api/apiService'
import type { Source } from '@/types/source'

function failSource(error: unknown): string {
    const message = apiErrorMessage(error, 'Server didn\'t respond')
    if (isLimitError(error)) {
        toast.add({ type: 'error', title: message })
    }
    return message
}

export const useSources = (conversationId: string | null) => {
    const queryClient = useQueryClient()

    return useAuthQuery({
        queryKey: ['conversation-sources', conversationId],
        queryFn: async ({ queryKey }): Promise<Source[]> => {
            const response = await apiService.getSources(conversationId as string)
            return mergeFetchedSources(
                queryClient.getQueryData<Source[]>(queryKey),
                response.conversationSources,
            )
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

    const addSource = async (source: Source) => {
        await queryClient.cancelQueries({ queryKey })
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

    const replaceSource = async (sourceId: string, nextSource: Source) => {
        await queryClient.cancelQueries({ queryKey })
        queryClient.setQueryData<Source[]>(queryKey, (current = []) => replaceSourceInList(current, sourceId, nextSource))
    }

    const addUrlSource = async (url: string) => {
        conversation?.armConversationEvents()
        const pendingSource = createPendingSource(url, 'video/youtube')
        await addSource(pendingSource)

        try {
            const source = await apiService.addUrlSource(conversationId, url)
            await replaceSource(pendingSource.id, source)
            bumpSourceCount(conversationId, 1)
        }
        catch (error) {
            await replaceSource(pendingSource.id, rejectSource(pendingSource, failSource(error)))
        }
    }

    const uploadSource = async (file: File) => {
        conversation?.armConversationEvents()
        const pendingSource = createPendingSource(file.name, file.type || null)
        await addSource(pendingSource)

        try {
            const formData = new FormData()
            formData.append('file', file)
            const source = await apiService.uploadSource(conversationId, formData)
            await replaceSource(pendingSource.id, source)
            bumpSourceCount(conversationId, 1)
        }
        catch (error) {
            await replaceSource(pendingSource.id, rejectSource(pendingSource, failSource(error)))
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
