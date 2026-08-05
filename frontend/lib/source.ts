import type { UploadSourceResponse } from '@/services/api/types'
import type { Source } from '@/types/source'

export function createPendingSource(file: File): Source {
    return {
        id: crypto.randomUUID(),
        filename: file.name,
        contentType: file.type || null,
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
