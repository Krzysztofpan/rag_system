import { ArrowLeft, Trash2 } from 'lucide-react'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'

import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

import NoteToolbar from './NoteToolbar'

type NoteViewProps = {
    title?: string;
    initialContent?: string;
    onBack?: () => void;
    onDelete?: () => void;
    onContentChange?: (html: string) => void;
}

const NoteView = ({
    title = 'New note',
    initialContent = '',
    onBack,
    onDelete,
    onContentChange,
}: NoteViewProps) => {
    const editor = useEditor({
        immediatelyRender: false,
        extensions: [
            StarterKit.configure({
                heading: { levels: [1, 2, 3] },
                link: false,
            }),
            Link.configure({
                openOnClick: false,
                HTMLAttributes: { class: 'note-editor-link' },
            }),
            Image.configure({
                HTMLAttributes: { class: 'note-editor-image' },
            }),
            Placeholder.configure({
                placeholder: 'Start writing…',
            }),
        ],
        content: initialContent,
        editorProps: {
            attributes: {
                class: 'note-editor-content focus:outline-none',
            },
        },
        onUpdate: ({ editor: current }) => {
            onContentChange?.(current.getHTML())
        },
    })

    return (
        <div className="flex h-full min-h-0 flex-col overflow-hidden bg-sidebar text-sidebar-foreground">
            <header className="flex h-12 shrink-0 items-center justify-between gap-3 px-3">
                <div className="flex min-w-0 items-center gap-1">
                    {onBack && (
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon-sm"
                            aria-label="Back to studio"
                            onClick={onBack}
                            className="shrink-0 text-muted-foreground"
                        >
                            <ArrowLeft />
                        </Button>
                    )}
                    <h2 className="truncate text-sm font-medium">{title}</h2>
                </div>
                <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Delete note"
                    onClick={onDelete}
                    className="shrink-0 text-muted-foreground hover:text-destructive"
                >
                    <Trash2 />
                </Button>
            </header>

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
