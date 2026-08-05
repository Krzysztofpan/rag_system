import { useQuery, useQueryClient } from '@tanstack/react-query'

import { applyUploadResponse, createPendingSource, rejectSource } from '@/lib/source'
import { apiService } from '@/services/api/apiService'
import type { Source } from '@/types/source'

export const sourcesQueryKey = (conversationId: string) =>
    ['conversation-sources', conversationId] as const

export const useSources = (conversationId: string) => {
    return useQuery<Source[]>({
        queryKey: sourcesQueryKey(conversationId),
        queryFn: async (): Promise<Source[]> => {
            const response = await apiService.getSources(conversationId)
            return response.conversationSources
        },
    })
}

export const useSourcesClient = (conversationId: string) => {
    const queryClient = useQueryClient()
    const queryKey = sourcesQueryKey(conversationId)

    const addSource = (source: Source) => {
        queryClient.setQueryData<Source[]>(queryKey, (current = []) => [
            ...current,
            source,
        ])
    }

    const deleteSource = (sourceId: string) => {
        queryClient.setQueryData<Source[]>(queryKey, (current = []) =>
            current.filter((source) => source.id !== sourceId),
        )
    }

    const replaceSource = (sourceId: string, nextSource: Source) => {
        queryClient.setQueryData<Source[]>(queryKey, (current = []) =>
            current.map((source) =>
                source.id === sourceId ? nextSource : source,
            ),
        )
    }

    const uploadSource = async (file: File) => {
        const pendingSource = createPendingSource(file)
        addSource(pendingSource)

        try {
            const formData = new FormData()
            formData.append('file', file)
            const body = await apiService.uploadSource(conversationId, formData)
            replaceSource(pendingSource.id, applyUploadResponse(pendingSource, body))
        }
        catch {
            replaceSource(
                pendingSource.id,
                rejectSource(pendingSource, 'Server didn\'t respond'),
            )
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
        replaceSource,
        uploadSource,
        editSourceName,
    }
}
