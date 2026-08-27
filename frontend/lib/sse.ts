export type ConversationTitleEvent = {
    event: 'conversation.title';
    conversationId: string;
    title: string;
}

export function parseConversationTitleEvent(data: string): ConversationTitleEvent | null {
    let parsed: unknown
    try {
        parsed = JSON.parse(data) as unknown
    }
    catch {
        return null
    }
    if (typeof parsed !== 'object' || parsed === null) {
        return null
    }
    const record = parsed as Record<string, unknown>
    if (record.event !== 'conversation.title') {
        return null
    }
    const conversationId = record.conversationId
    const title = record.title
    if (typeof conversationId !== 'string' || typeof title !== 'string' || !title) {
        return null
    }
    return {
        event: 'conversation.title',
        conversationId,
        title,
    }
}

export async function readSseDataFrames(
    body: ReadableStream<Uint8Array>,
    onData: (data: string) => void,
): Promise<void> {
    const reader = body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
        while (true) {
            const { done, value } = await reader.read()
            if (done) {
                break
            }
            buffer += decoder.decode(value, { stream: true })
            const frames = buffer.split('\n\n')
            buffer = frames.pop() ?? ''
            for (const frame of frames) {
                const data = sseFrameData(frame)
                if (data !== null) {
                    onData(data)
                }
            }
        }
    }
    finally {
        reader.releaseLock()
    }
}

function sseFrameData(frame: string): string | null {
    const dataLines = frame
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
    if (dataLines.length === 0) {
        return null
    }
    return dataLines.join('\n')
}
