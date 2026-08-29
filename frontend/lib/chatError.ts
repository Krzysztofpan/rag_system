import { apiErrorMessage, parseApiError } from './apiError'

export const PROMPT_ATTACK_MESSAGE =
    'This message was blocked for security reasons.'

export function chatSendErrorMessage(error: unknown): string {
    const info = parseApiError(error)
    const raw = info?.message ?? (error instanceof Error ? error.message : '')
    if (
        info?.code === 'prompt_attack'
        || raw.includes('prompt_attack')
        || raw.includes(PROMPT_ATTACK_MESSAGE)
    ) {
        return PROMPT_ATTACK_MESSAGE
    }
    return apiErrorMessage(error, 'Failed to send message')
}
