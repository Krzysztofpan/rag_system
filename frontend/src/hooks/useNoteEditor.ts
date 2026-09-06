import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import { useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'

type UseNoteEditorOptions = {
    content?: string;
    onContentChange?: (html: string) => void;
}

export function useNoteEditor({
    content = '',
    onContentChange,
}: UseNoteEditorOptions = {}) {
    return useEditor({
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
        content,
        editorProps: {
            attributes: {
                class: 'note-editor-content focus:outline-none',
            },
        },
        onUpdate: ({ editor: current }) => {
            onContentChange?.(current.getHTML())
        },
    })
}
