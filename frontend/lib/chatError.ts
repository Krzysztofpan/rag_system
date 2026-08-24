export const PROMPT_ATTACK_MESSAGE =
    'This message was blocked for security reasons.'

export function chatSendErrorMessage(error: unknown): string {
    const raw = error instanceof Error ? error.message : ''
    if (raw.includes('prompt_attack') || raw.includes(PROMPT_ATTACK_MESSAGE)) {
        return PROMPT_ATTACK_MESSAGE
    }
    return raw || 'Failed to send message'
}
