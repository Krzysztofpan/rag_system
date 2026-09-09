import ChatNoteView from '@/components/conversation/studio/note/ChatNoteView'
import NoteView from '@/components/conversation/studio/note/NoteView'
import { type OpenStudioNote, useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useDeleteResource } from '@/hooks/useDeleteResource'
import { useResources } from '@/hooks/useResources'
import useUpdateNoteResource from '@/hooks/useUpdateNoteResource'
import { isUnchangedUserNote, isUserNote, normalizeNoteTitle, userNoteContent } from '@/lib/note'
import { cn } from '@/lib/utils'
import type { NoteResource } from '@/services/api/types'

type OpenNotePanelProps = {
    note: OpenStudioNote;
}

function OpenNotePanel({ note }: OpenNotePanelProps) {
    const { conversationId, setStudioOpenNote: setOpenNote } = useConversationContext()
    const { data: resources } = useResources(conversationId)
    const { mutate: saveNote, isPending: isSavingNote } = useUpdateNoteResource(conversationId)
    const { mutate: deleteResource, isPending: isDeleting } = useDeleteResource(conversationId)

    const liveNote = resources?.find((resource): resource is NoteResource => (
        resource.type === 'note' && resource.id === note.id
    ))
    const title = liveNote?.title ?? note.title

    const handleLeaveUserNote = (html: string, nextTitle: string) => {
        if (isSavingNote) return
        if (!note.id) {
            setOpenNote(null)
            return
        }
        const normalizedTitle = normalizeNoteTitle(nextTitle)
        if (isUnchangedUserNote(note, html, normalizedTitle)) {
            setOpenNote(null)
            return
        }
        saveNote(
            {
                resourceId: note.id,
                content: userNoteContent(html),
                title: normalizedTitle,
            },
            { onSuccess: () => setOpenNote(null) },
        )
    }

    const handleLeaveChatNote = (nextTitle: string) => {
        if (isSavingNote) return
        if (!note.id) {
            setOpenNote(null)
            return
        }
        const normalizedTitle = normalizeNoteTitle(nextTitle)
        const currentTitle = liveNote?.title ?? note.title
        if (normalizedTitle === currentTitle) {
            setOpenNote(null)
            return
        }
        saveNote(
            {
                resourceId: note.id,
                title: normalizedTitle,
            },
            { onSuccess: () => setOpenNote(null) },
        )
    }

    const handleDelete = () => {
        if (note.id) {
            deleteResource(note.id)
        }
        setOpenNote(null)
    }

    return (
        <aside
            className={cn(
                'flex h-full relative shrink-0 flex-col overflow-hidden rounded-xl',
                'bg-sidebar text-sidebar-foreground ring-1 ring-sidebar-border',
                'transition-[width] duration-200 ease-linear',
                'w-[min(46vw,40rem)]',
            )}
        >
            {isUserNote(note.content)
                ? (
                        <NoteView
                            key={note.id ?? 'new-note'}
                            title={title}
                            initialContent={note.content.html}
                            isSaving={isSavingNote}
                            onBack={handleLeaveUserNote}
                            onDelete={handleDelete}
                            isDeleting={isDeleting}
                        />
                    )
                : (
                        <ChatNoteView
                            key={note.id ?? 'chat-note'}
                            title={title}
                            markdown={note.content.markdown}
                            sources={note.content.sources}
                            onBack={handleLeaveChatNote}
                            onDelete={handleDelete}
                            isSaving={isSavingNote}
                            isDeleting={isDeleting}
                        />
                    )}
        </aside>
    )
}

export default OpenNotePanel
