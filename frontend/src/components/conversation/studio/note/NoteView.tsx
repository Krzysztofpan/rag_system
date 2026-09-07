import { EditorContent } from '@tiptap/react'

import { Separator } from '@/components/ui/separator'
import { useNoteEditor } from '@/hooks/useNoteEditor'

import NoteHeader from './NoteHeader'
import NoteToolbar from './NoteToolbar'

type NoteViewProps = {
    title?: string;
    initialContent?: string;
    isSaving?: boolean;
    onBack: (html: string) => void;
    onDelete: () => void;
    isDeleting?: boolean;
    onContentChange?: (html: string) => void;
}

const NoteView = ({
    title = 'New note',
    initialContent = '',
    isSaving = false,
    onBack,
    onDelete,
    isDeleting,
    onContentChange,
}: NoteViewProps) => {
    const editor = useNoteEditor({
        content: initialContent,
        onContentChange,
    })

    const handleBack = () => {
        if (isSaving) return
        onBack(editor?.getHTML() ?? initialContent)
    }

    return (
        <div className="flex h-full min-h-0 flex-col overflow-hidden bg-sidebar text-sidebar-foreground">
            <NoteHeader
                title={title}
                onBack={handleBack}
                onDelete={onDelete}
                isSaving={isSaving}
                isDeleting={isDeleting}
            />

            <Separator />

            {editor && <NoteToolbar editor={editor} />}

            <Separator />

            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
                <EditorContent editor={editor} className="note-editor h-full" />
            </div>
        </div>
    )
}

export default NoteView
