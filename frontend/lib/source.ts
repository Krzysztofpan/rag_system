import type { Source } from '@/types/source'

export function createPendingSource(name: string, type: string | null): Source {
    return {
        id: crypto.randomUUID(),
        filename: name,
        contentType: type,
        status: 'pending',
        error: null,
    }
}

export function rejectSource(source: Source, error: string): Source {
    return { ...source, status: 'failed', error }
}
