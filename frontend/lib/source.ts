import type { UploadSourceResponse } from '@/services/api/types'
import type { Source } from '@/types/source'

export function createPendingSource(name: string, type: string | null): Source {
    return {
        id: crypto.randomUUID(),
        filename: name,
        contentType: type,
        status: 'pending',
        error: null,
        chunkCount: 0,
    }
}

export function applyUploadResponse(source: Source, body: UploadSourceResponse): Source {
    if (body.source == null) {
        return {
            ...source,
            status: 'failed',
            error: body.error,
        }
    }

    return {
        ...source,
        ...body.source,
        error: body.error ?? body.source.error,
    }
}

export function rejectSource(source: Source, error: string): Source {
    return { ...source, status: 'failed', error }
}
