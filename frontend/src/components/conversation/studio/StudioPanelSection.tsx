import { conversationPanelClassName } from '@/components/conversation/conversationPanel'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger, useSidebar } from '@/components/ui/sidebar'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import useCreateNoteResource from '@/hooks/useCreateNoteResource'
import { DEFAULT_NOTE_TITLE, userNoteContent } from '@/lib/note'
import type { CreateNoteResponse, NoteResource, Resource } from '@/services/api/types'

import OpenNotePanel from './note/OpenNotePanel'
import CreateNoteBtn from './CreateNoteBtn'
import CreateResourceItemType from './CreateResourceItemType'
import ResourcesSection from './ResourcesSection'
import { resourcesItems } from './studio.contants'

function StudioPanelSection() {
    const { state, setOpen } = useSidebar()
    const isCollapsed = state === 'collapsed'
    const {
        conversationId,
        studioOpenNote: openNote,
        openStudioNote,
    } = useConversationContext()
    const { mutate, isPending } = useCreateNoteResource(conversationId)

    const handleCreateNote = () => {
        mutate({ title: DEFAULT_NOTE_TITLE, content: userNoteContent() }, {
            onSuccess: ({ resource }: CreateNoteResponse) => {
                setOpen(true)
                openStudioNote(resource)
            },
        })
    }

    const openNoteView = (resource: NoteResource) => {
        setOpen(true)
        openStudioNote(resource)
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
        return <OpenNotePanel note={openNote} />
    }

    return (
        <aside
            className={conversationPanelClassName(
                'relative',
                isCollapsed ? 'md:w-(--sidebar-width-icon)' : 'md:w-(--sidebar-width)',
            )}
        >
            <div className={`hidden h-12 shrink-0 items-center gap-2 px-2 md:flex ${isCollapsed ? 'justify-center' : 'justify-between pl-4'}`}>
                {!isCollapsed && <span className="truncate font-medium">Studio</span>}
                <SidebarTrigger />
            </div>
            <Separator className="hidden md:block" />
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
                <div className={`grid ${!isCollapsed ? 'grid-cols-2 px-5' : 'px-2'} py-3 gap-2`}>
                    {resourcesItems.map((resource) => (
                        <CreateResourceItemType
                            key={resource.type}
                            displayName={resource.name}
                            type={resource.type}
                            color={resource.color}
                            icon={resource.icon}
                            unavailable={resource.unavailable ?? false}
                        />
                    ))}
                </div>
                <Separator />
                <ResourcesSection isCreatingNote={isPending} onOpenResource={handleOpenResource} />
            </div>
            <CreateNoteBtn onOpenNote={handleCreateNote} />
        </aside>
    )
}

export default StudioPanelSection
