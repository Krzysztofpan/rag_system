import { useState } from 'react'

import MarkdownContent from '@/components/conversation/conversationView/MarkdownContent'
import { Separator } from '@/components/ui/separator'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { DEFAULT_NOTE_TITLE } from '@/lib/note'
import type { MessageSource } from '@/types/citation'

import NoteHeader from './NoteHeader'

type ChatNoteViewProps = {
    title?: string;
    markdown: string;
    sources?: MessageSource[];
    onBack: (title: string) => void;
    onDelete: () => void;
    isSaving?: boolean;
    isDeleting?: boolean;
}

const ChatNoteView = ({
    title: initialTitle = DEFAULT_NOTE_TITLE,
    markdown,
    sources = [],
    onBack,
    onDelete,
    isSaving = false,
    isDeleting,
}: ChatNoteViewProps) => {
    const { conversationId } = useConversationContext()
    const [draftTitle, setDraftTitle] = useState<string | null>(null)
    const title = draftTitle ?? initialTitle

    const handleBack = () => {
        if (isSaving) return
        onBack(title)
    }

    return (
        <div className="flex h-full min-h-0 flex-col overflow-hidden bg-sidebar text-sidebar-foreground">
            <NoteHeader
                title={title}
                onTitleChange={setDraftTitle}
                onBack={handleBack}
                onDelete={onDelete}
                isSaving={isSaving}
                isDeleting={isDeleting}
            />
            <Separator />
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
                <MarkdownContent
                    content={markdown}
                    className="max-w-full"
                    conversationId={conversationId}
                    sources={sources}
                />
            </div>
        </div>
    )
}

export default ChatNoteView
