import type { Source } from '@/types/source'

const OPTIMISTIC_SOURCE_ID_PREFIX = 'pending:'

export function createPendingSource(name: string, type: string | null): Source {
    return {
        id: `${OPTIMISTIC_SOURCE_ID_PREFIX}${crypto.randomUUID()}`,
        filename: name,
        contentType: type,
        status: 'pending',
        error: null,
    }
}

export function rejectSource(source: Source, error: string): Source {
    return { ...source, status: 'failed', error }
}

export function isOptimisticSourceId(sourceId: string): boolean {
    return sourceId.startsWith(OPTIMISTIC_SOURCE_ID_PREFIX)
}

function isOptimisticSource(source: Source): boolean {
    return isOptimisticSourceId(source.id)
}

export function mergeFetchedSources(cached: Source[] | undefined, fetched: Source[]): Source[] {
    if (!cached?.length) {
        return fetched
    }

    const fetchedIds = new Set(fetched.map((source) => source.id))
    const optimistic = cached.filter((source) => isOptimisticSource(source) && !fetchedIds.has(source.id))
    if (optimistic.length === 0) {
        return fetched
    }

    return [...fetched, ...optimistic]
}

export function replaceSourceInList(sources: Source[], sourceId: string, nextSource: Source): Source[] {
    const index = sources.findIndex((source) => source.id === sourceId)
    if (index === -1) {
        return sources.some((source) => source.id === nextSource.id) ? sources : [...sources, nextSource]
    }

    const next = [...sources]
    next[index] = nextSource
    if (nextSource.id === sourceId) {
        return next
    }

    return next.filter((source, i) => i === index || source.id !== nextSource.id)
}
