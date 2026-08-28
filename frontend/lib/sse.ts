import { CONVERSATION_TOPICS, type ConversationTopicName } from '@/lib/conversationTopic'

export type ConversationUpdatedEvent = {
    event: 'conversation.updated';
    conversationId: string;
    title: string;
    topic: ConversationTopicName;
    documentsSummary: string | null;
}

export function parseConversationUpdatedEvent(data: string): ConversationUpdatedEvent | null {
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
    if (record.event !== 'conversation.updated') {
        return null
    }
    const conversationId = record.conversationId
    const title = record.title
    const topic = record.topic
    if (typeof conversationId !== 'string' || typeof title !== 'string' || !title) {
        return null
    }
    if (typeof topic !== 'string') {
        return null
    }
    const allowedTopics: readonly string[] = CONVERSATION_TOPICS
    if (!allowedTopics.includes(topic)) {
        return null
    }
    const documentsSummaryValue = record.documentsSummary
    if (documentsSummaryValue !== undefined && documentsSummaryValue !== null && typeof documentsSummaryValue !== 'string') {
        return null
    }
    return {
        event: 'conversation.updated',
        conversationId,
        title,
        topic: topic as ConversationTopicName,
        documentsSummary: typeof documentsSummaryValue === 'string' ? documentsSummaryValue : null,
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
