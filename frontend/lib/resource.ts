import type { UploadResourceResponse } from '@/services/api/types'
import type { Resource } from '@/types/resource'

export function createPendingResource(file: File): Resource {
    return {
        id: crypto.randomUUID(),
        filename: file.name,
        contentType: file.type || null,
        status: 'pending',
        error: null,
        chunkCount: 0,
    }
}

export function applyUploadResponse(resource: Resource, body: UploadResourceResponse): Resource {
    if (body.resource == null) {
        return {
            ...resource,
            status: 'failed',
            error: body.error,
        }
    }

    return {
        ...resource,
        ...body.resource,
        error: body.error ?? body.resource.error,
    }
}

export function rejectResource(resource: Resource, error: string): Resource {
    return { ...resource, status: 'failed', error }
}
