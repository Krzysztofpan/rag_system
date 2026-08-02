import type { Resource } from '@/types/resource'
import type { UploadResourceResponse } from '@/types/upload'

export function createPendingResource(file: File): Resource {
    return {
        id: crypto.randomUUID(),
        file,
        status: 'pending',
        documentId: null,
        parsedContent: null,
        quality: null,
        error: null,
    }
}

export function applyUploadResponse(resource: Resource, body: UploadResourceResponse): Resource {
    return {
        ...resource,
        status: body.status,
        documentId: body.document_id,
        parsedContent: body.parsed_content,
        quality: body.quality,
        error: body.error,
    }
}

export function rejectResource(resource: Resource, error: string): Resource {
    return { ...resource, status: 'rejected', error }
}
