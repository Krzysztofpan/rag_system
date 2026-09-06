import { useState } from 'react'

import NoteView from '@/components/conversation/studio/note/NoteView'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger, useSidebar } from '@/components/ui/sidebar'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import useCreateNoteResource from '@/hooks/useCreateNoteResource'
import { cn } from '@/lib/utils'
import type { CreateNoteResponse, NoteResource, Resource } from '@/services/api/types'

import CreateResourceItemType from './CreateResourceItemType'
import ResourcesSection from './ResourcesSection'
import { resourcesItems } from './studio.contants'

type OpenNoteState = {
    id?: string;
    title: string;
    text: string;
}

function StudioPanelSection() {
    const { state, setOpen } = useSidebar()
    const [openNote, setOpenNote] = useState<OpenNoteState | null>(null)
    const isCollapsed = state === 'collapsed'
    const { conversationId } = useConversationContext()
    const { mutate, isPending } = useCreateNoteResource(conversationId)

    const handleCreateNote = () => {
        mutate(undefined, {
            onSuccess: ({ resource }: CreateNoteResponse) => {
                setOpen(true)
                setOpenNote({ text: resource.content.text, title: resource.title })
            },
        })
    }

    const openNoteView = (resource: NoteResource) => {
        setOpen(true)
        setOpenNote({
            id: resource.id,
            title: resource.title,
            text: resource.content.text,
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
                <NoteView
                    key={openNote.id ?? 'new-note'}
                    title={openNote.title}
                    initialContent={openNote.text}
                    onBack={() => setOpenNote(null)}
                />
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
