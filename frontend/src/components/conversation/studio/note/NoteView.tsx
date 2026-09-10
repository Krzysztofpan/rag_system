import { useState } from 'react'
import { EditorContent } from '@tiptap/react'

import { Separator } from '@/components/ui/separator'
import { useNoteEditor } from '@/hooks/useNoteEditor'
import { DEFAULT_NOTE_TITLE } from '@/lib/note'

import NoteHeader from './NoteHeader'
import NoteToolbar from './NoteToolbar'

import './note-editor.css'

type NoteViewProps = {
    title?: string;
    initialContent?: string;
    isSaving?: boolean;
    onBack: (html: string, title: string) => void;
    onDelete: () => void;
    isDeleting?: boolean;
    onContentChange?: (html: string) => void;
}

const NoteView = ({
    title: initialTitle = DEFAULT_NOTE_TITLE,
    initialContent = '',
    isSaving = false,
    onBack,
    onDelete,
    isDeleting,
    onContentChange,
}: NoteViewProps) => {
    const [title, setTitle] = useState(initialTitle)
    const editor = useNoteEditor({
        content: initialContent,
        onContentChange,
    })

    const handleBack = () => {
        if (isSaving) return
        onBack(editor?.getHTML() ?? initialContent, title)
    }

    return (
        <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-sidebar text-sidebar-foreground">
            <NoteHeader
                title={title}
                onTitleChange={setTitle}
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
