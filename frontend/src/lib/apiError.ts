import { isAxiosError } from 'axios'

const LIMIT_CODES = new Set([
    'max_upload_bytes',
    'max_ingests_per_day',
    'max_messages_per_day',
    'max_conversations',
    'max_messages_per_conversation',
])

export type ApiErrorInfo = {
    message: string;
    code?: string;
    status?: number;
    limit?: number;
    current?: number;
}

export class ApiRequestError extends Error {
    readonly code?: string
    readonly status?: number
    readonly limit?: number
    readonly current?: number

    constructor(info: ApiErrorInfo) {
        super(info.message)
        this.name = 'ApiRequestError'
        this.code = info.code
        this.status = info.status
        this.limit = info.limit
        this.current = info.current
    }
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null
}

function formatByteLimit(bytes: number): string {
    const mb = bytes / (1024 * 1024)
    if (Number.isInteger(mb)) {
        return `${mb} MB`
    }
    return `${mb.toFixed(1)} MB`
}

export function limitUserMessage(code: string, limit?: number): string | null {
    switch (code) {
        case 'max_conversations':
            return limit != null
                ? `You've reached the conversation limit (${limit}). Delete a conversation to create a new one.`
                : 'You\'ve reached the conversation limit. Delete a conversation to create a new one.'
        case 'max_messages_per_conversation':
            return limit != null
                ? `This conversation has reached the ${limit} message limit.`
                : 'This conversation has reached the message limit.'
        case 'max_messages_per_day':
            return limit != null
                ? `You've reached today's message limit (${limit}). Try again tomorrow.`
                : 'You\'ve reached today\'s message limit. Try again tomorrow.'
        case 'max_ingests_per_day':
            return limit != null
                ? `You've reached today's source limit (${limit}). Try again tomorrow.`
                : 'You\'ve reached today\'s source limit. Try again tomorrow.'
        case 'max_upload_bytes':
            return limit != null
                ? `This file is too large. Maximum size is ${formatByteLimit(limit)}.`
                : 'This file is too large.'
        default:
            return null
    }
}

function nestedDetail(payload: unknown): unknown {
    if (isRecord(payload) && 'detail' in payload) {
        return payload.detail
    }
    return payload
}

function fromDetail(detail: unknown, status?: number): ApiErrorInfo | null {
    if (typeof detail === 'string' && detail) {
        return { message: detail, status }
    }
    if (!isRecord(detail)) {
        return null
    }

    const code = typeof detail.code === 'string' ? detail.code : undefined
    const limit = typeof detail.limit === 'number' ? detail.limit : undefined
    const current = typeof detail.current === 'number' ? detail.current : undefined
    const backendMessage = typeof detail.message === 'string' ? detail.message : undefined
    const mapped = code ? limitUserMessage(code, limit) : null
    const message = mapped ?? backendMessage
    if (!message) {
        return null
    }
    return { message, code, status, limit, current }
}

function fromJsonPayload(payload: unknown, status?: number): ApiErrorInfo | null {
    return fromDetail(nestedDetail(payload), status) ?? fromDetail(payload, status)
}

function fromWrappedHttpError(raw: string, status?: number): ApiErrorInfo | null {
    const jsonStart = raw.indexOf('{')
    if (jsonStart === -1) {
        return null
    }
    try {
        return fromJsonPayload(JSON.parse(raw.slice(jsonStart)) as unknown, status)
    }
    catch {
        return null
    }
}

function protocolCode(error: Error): string | undefined {
    if (error.name !== 'ProtocolError' || !('code' in error)) {
        return undefined
    }
    return typeof error.code === 'string' ? error.code : undefined
}

export function parseApiError(error: unknown): ApiErrorInfo | null {
    if (error instanceof ApiRequestError) {
        return {
            message: error.message,
            code: error.code,
            status: error.status,
            limit: error.limit,
            current: error.current,
        }
    }

    if (isAxiosError(error)) {
        const status = error.response?.status
        return fromJsonPayload(error.response?.data, status)
            ?? (error.message ? { message: error.message, status } : null)
    }

    if (!(error instanceof Error) || !error.message) {
        return null
    }

    const code = protocolCode(error)
    if (code) {
        return {
            message: limitUserMessage(code) ?? error.message,
            code,
        }
    }

    return fromWrappedHttpError(error.message) ?? { message: error.message }
}

export function apiErrorMessage(error: unknown, fallback: string): string {
    return parseApiError(error)?.message ?? fallback
}

export function isLimitError(error: unknown): boolean {
    const info = parseApiError(error)
    if (!info) {
        return false
    }
    if (info.code && LIMIT_CODES.has(info.code)) {
        return true
    }
    return info.status === 429 || info.status === 413
}

export async function rejectOnApiError(response: Response): Promise<Response> {
    if (response.status !== 429 && response.status !== 413) {
        return response
    }
    const info = await apiErrorFromResponse(response)
    throw new ApiRequestError(info ?? {
        message: `Request failed (${response.status})`,
        status: response.status,
    })
}

export async function apiErrorFromResponse(response: Response): Promise<ApiErrorInfo | null> {
    try {
        return fromJsonPayload(await response.json() as unknown, response.status)
    }
    catch {
        return {
            message: response.statusText || `Request failed (${response.status})`,
            status: response.status,
        }
    }
}
