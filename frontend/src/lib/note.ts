import type { ChatNoteContent, NoteContent, UserNoteContent } from '@/services/api/types'
import type { Message } from '@/types/Message'

export function isUserNote(content: NoteContent): content is UserNoteContent {
    return content.kind === 'user'
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
