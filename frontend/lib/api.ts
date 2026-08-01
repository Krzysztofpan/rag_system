import type { Resource } from '@/types/resource'
import type { ApiErrorResponse, UploadQuality, UploadResponse } from '@/types/upload'

const backendUrl = import.meta.env.VITE_BACKEND_URL

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

export async function uploadResource(resource: Resource, conversationId: string): Promise<Resource> {
    const formData = new FormData()
    formData.append('file', resource.file)

    let response: Response
    try {
        response = await fetch(`${backendUrl}/upload?conversation_id=${conversationId}`, {
            method: 'POST',
            body: formData,
        })
    }
    catch {
        return { ...resource, status: 'rejected', error: 'Server didn\'t respond' }
    }

    const body = (await response.json()) as UploadResponse | ApiErrorResponse

    if (!('status' in body)) {
        return { ...resource, status: 'rejected', error: body.detail }
    }

    if (body.status === 'ok') {
        return {
            ...resource,
            status: 'ready',
            documentId: body.document_id,
            parsedContent: body.parsed_content,
            quality: body.quality,
            error: null,
        }
    }

    return {
        ...resource,
        status: 'rejected',
        documentId: body.document_id,
        quality: normalizeRejectedQuality(body.report),
        error: body.detail,
    }
}

/**
 * Przy 422 backend zwraca raport parsera rozpłaszczony na wierzchu, a nie
 * pod kluczem parse_report. Sprowadzamy go do tego samego kształtu co przy 200,
 * żeby UI miał jedną reprezentację jakości.
 */
function normalizeRejectedQuality(report: Extract<UploadResponse, { status: 'rejected' }>['report']): UploadQuality {
    const { chunk_quality, ...parseReport } = report
    return { parse_report: parseReport, chunk_quality }
}
