import { useAuthQuery } from '@/hooks/useAuthQuery'
import { apiService } from '@/services/api/apiService'
import type { MessageSource } from '@/types/Message'

export type CitationPreview = {
    title: string;
    body: string;
}

function pagesLabel(pages: number[] | null): string {
    return pages?.length ? ` · s. ${pages.join(', ')}` : ''
}

function sourcePointer(source: MessageSource): string {
    switch (source.kind) {
        case 'chunk':
            return source.chunkId
        case 'summary':
            return source.documentId
        case 'web':
            return source.url
    }
}

async function getCitationPreview(
    conversationId: string,
    source: MessageSource,
): Promise<CitationPreview> {
    switch (source.kind) {
        case 'chunk': {
            const chunk = await apiService.getChunk(conversationId, source.chunkId)
            return {
                title: `${chunk.filename}${pagesLabel(chunk.pages)}`,
                body: chunk.content,
            }
        }
        case 'summary': {
            const report = await apiService.getSourceReport(
                conversationId,
                source.documentId,
            )
            return {
                title: 'Podsumowanie dokumentu',
                body: report.summary || 'Brak podsumowania.',
            }
        }
        case 'web':
            return { title: '', body: '' }
    }
}

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
