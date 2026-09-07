import MarkdownContent from '@/components/conversation/conversationView/MarkdownContent'
import { Separator } from '@/components/ui/separator'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import type { MessageSource } from '@/types/citation'

import NoteHeader from './NoteHeader'

type ChatNoteViewProps = {
    title?: string;
    markdown: string;
    sources?: MessageSource[];
    onBack: () => void;
    onDelete?: () => void;
}

const ChatNoteView = ({
    title = 'New note',
    markdown,
    sources = [],
    onBack,
    onDelete,
}: ChatNoteViewProps) => {
    const { conversationId } = useConversationContext()

    return (
        <div className="flex h-full min-h-0 flex-col overflow-hidden bg-sidebar text-sidebar-foreground">
            <NoteHeader title={title} onBack={onBack} onDelete={onDelete} />
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
