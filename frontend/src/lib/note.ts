import type { ChatNoteContent, NoteContent, NoteResource, Resource, UserNoteContent } from '@/services/api/types'
import type { Message } from '@/types/Message'

export function isUserNote(content: NoteContent): content is UserNoteContent {
    return content.kind === 'user'
}

function htmlToPlainText(html: string): string {
    return html
        .replace(/<br\s*\/?>/gi, '\n')
        .replace(/<\/(?:p|div|h[1-6]|li)>/gi, '\n')
        .replace(/<[^>]+>/g, '')
        .replace(/&nbsp;/gi, ' ')
        .replace(/\s+/g, ' ')
        .trim()
}

export function noteHasContent(content: NoteContent): boolean {
    if (content.kind === 'chat') {
        return content.markdown.trim().length > 0
    }
    return htmlToPlainText(content.html).length > 0
}

export function isUnchangedUserNote(content: NoteContent, html: string): boolean {
    return isUserNote(content) && content.html === html
}

export function userNoteContent(html = ''): UserNoteContent {
    return { kind: 'user', html }
}

export function chatNoteFromMessage(message: Message): ChatNoteContent {
    return {
        kind: 'chat',
        markdown: message.text,
        messageId: message.id,
        sources: message.sources,
    }
}

export function chatNoteForMessage(
    resources: Resource[] | undefined,
    messageId: string,
): NoteResource | undefined {
    return resources?.find((resource): resource is NoteResource => (
        resource.type === 'note'
        && resource.content.kind === 'chat'
        && resource.content.messageId === messageId
    ))
}
