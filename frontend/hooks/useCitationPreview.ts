import { useAuthQuery } from '@/hooks/useAuthQuery'
import { getCitationPreview, sourcePointer } from '@/lib/citations'
import type { MessageSource } from '@/types/citation'

export function useCitationPreview(
    conversationId: string,
    source: MessageSource,
    enabled: boolean,
) {
    return useAuthQuery({
        queryKey: [
            'citation-preview',
            conversationId,
            source.kind,
            source.index,
            sourcePointer(source),
        ],
        queryFn: () => getCitationPreview(conversationId, source),
        enabled,
        staleTime: Infinity,
    })
}
