import { useState } from 'react'

import ChatNoteView from '@/components/conversation/studio/note/ChatNoteView'
import NoteView from '@/components/conversation/studio/note/NoteView'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger, useSidebar } from '@/components/ui/sidebar'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import useCreateNoteResource from '@/hooks/useCreateNoteResource'
import { useDeleteResource } from '@/hooks/useDeleteResource'
import { useResources } from '@/hooks/useResources'
import useUpdateNoteResource from '@/hooks/useUpdateNoteResource'
import { isUnchangedUserNote, isUserNote, userNoteContent } from '@/lib/note'
import { cn } from '@/lib/utils'
import type { CreateNoteResponse, NoteContent, NoteResource, Resource } from '@/services/api/types'

import CreateResourceItemType from './CreateResourceItemType'
import ResourcesSection from './ResourcesSection'
import { resourcesItems } from './studio.contants'

type OpenNoteState = {
    id?: string;
    title: string;
    content: NoteContent;
}

function StudioPanelSection() {
    const { state, setOpen } = useSidebar()
    const [openNote, setOpenNote] = useState<OpenNoteState | null>(null)
    const isCollapsed = state === 'collapsed'
    const { conversationId } = useConversationContext()
    const { data: resources } = useResources(conversationId)
    const { mutate, isPending } = useCreateNoteResource(conversationId)
    const { mutate: saveNote, isPending: isSavingNote } = useUpdateNoteResource(conversationId)
    const { mutate: deleteResource, isPending: isDeleting } = useDeleteResource(conversationId)

    const handleCreateNote = () => {
        mutate({ title: 'New Note', content: userNoteContent() }, {
            onSuccess: ({ resource }: CreateNoteResponse) => {
                setOpen(true)
                setOpenNote({
                    id: resource.id,
                    title: resource.title,
                    content: resource.content,
                })
            },
        })
    }

    const openNoteView = (resource: NoteResource) => {
        setOpen(true)
        setOpenNote({
            id: resource.id,
            title: resource.title,
            content: resource.content,
        })
    }

    const handleOpenResource = (resource: Resource) => {
        switch (resource.type) {
            case 'note':
                openNoteView(resource)
                break
            default:
                break
        }
    }

    const handleLeaveUserNote = (html: string) => {
        if (isSavingNote) return
        if (!openNote?.id) {
            setOpenNote(null)
            return
        }
        if (isUnchangedUserNote(openNote.content, html)) {
            setOpenNote(null)
            return
        }
        saveNote(
            {
                resourceId: openNote.id,
                content: userNoteContent(html),
            },
            { onSuccess: () => setOpenNote(null) },
        )
    }

    const handleDeleteOpenNote = () => {
        if (openNote?.id) {
            deleteResource(openNote.id)
        }
        setOpenNote(null)
    }

    const liveOpenNote = resources?.find((resource): resource is NoteResource => (
        resource.type === 'note' && resource.id === openNote?.id
    ))
    const openNoteTitle = liveOpenNote?.title ?? openNote?.title ?? ''

    if (openNote) {
        return (
            <aside
                className={cn(
                    'flex h-full relative shrink-0 flex-col overflow-hidden rounded-xl',
                    'bg-sidebar text-sidebar-foreground ring-1 ring-sidebar-border',
                    'transition-[width] duration-200 ease-linear',
                    'w-[min(46vw,40rem)]',
                )}
            >
                {isUserNote(openNote.content)
                    ? (
                            <NoteView
                                key={openNote.id ?? 'new-note'}
                                title={openNoteTitle}
                                initialContent={openNote.content.html}
                                isSaving={isSavingNote}
                                onBack={handleLeaveUserNote}
                                onDelete={handleDeleteOpenNote}
                                isDeleting={isDeleting}
                            />
                        )
                    : (
                            <ChatNoteView
                                key={openNote.id ?? 'chat-note'}
                                title={openNoteTitle}
                                markdown={openNote.content.markdown}
                                sources={openNote.content.sources}
                                onBack={() => setOpenNote(null)}
                                onDelete={handleDeleteOpenNote}
                                isDeleting={isDeleting}
                            />
                        )}
            </aside>
        )
    }

    return (
        <aside
            className={cn(
                'flex h-full relative shrink-0 flex-col overflow-hidden rounded-xl',
                'bg-sidebar text-sidebar-foreground ring-1 ring-sidebar-border',
                'transition-[width] duration-200 ease-linear',
                isCollapsed ? 'w-(--sidebar-width-icon)' : 'w-(--sidebar-width)',
            )}
        >
            <div className={`flex h-12 shrink-0 items-center gap-2 px-2 ${isCollapsed ? 'justify-center' : 'justify-between pl-4'}`}>
                {!isCollapsed && <span className="truncate font-medium">Studio</span>}
                <SidebarTrigger />
            </div>
            <Separator />
            <div className={`grid ${!isCollapsed ? 'grid-cols-2 px-5' : 'px-2'} py-3 gap-2`}>
                {resourcesItems.map((resource) => (
                    <CreateResourceItemType
                        key={resource.type}
                        displayName={resource.name}
                        type={resource.type}
                        color={resource.color}
                        icon={resource.icon}
                    />
                ))}
            </div>
            <Separator />
            <ResourcesSection isCreatingNote={isPending} handleCreateNote={handleCreateNote} onOpenResource={handleOpenResource} />

        </aside>
    )
}

export default StudioPanelSection
