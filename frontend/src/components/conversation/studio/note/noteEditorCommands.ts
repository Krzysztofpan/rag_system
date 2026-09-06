import type { Editor } from '@tiptap/react'

import { applyTextStyle, getActiveTextStyle, type TextStyle } from './noteTextStyle'

export function createNoteEditorCommands(editor: Editor) {
    return {
        undo: () => {
            editor.chain().focus().undo().run()
        },
        redo: () => {
            editor.chain().focus().redo().run()
        },
        canUndo: () => editor.can().undo(),
        canRedo: () => editor.can().redo(),

        getTextStyle: () => getActiveTextStyle(editor),
        setTextStyle: (style: TextStyle) => {
            applyTextStyle(editor, style)
        },

        toggleBold: () => {
            editor.chain().focus().toggleBold().run()
        },
        toggleItalic: () => {
            editor.chain().focus().toggleItalic().run()
        },
        toggleCode: () => {
            editor.chain().focus().toggleCode().run()
        },
        toggleCodeBlock: () => {
            editor.chain().focus().toggleCodeBlock().run()
        },
        toggleBulletList: () => {
            editor.chain().focus().toggleBulletList().run()
        },
        toggleOrderedList: () => {
            editor.chain().focus().toggleOrderedList().run()
        },
        toggleBlockquote: () => {
            editor.chain().focus().toggleBlockquote().run()
        },
        setHorizontalRule: () => {
            editor.chain().focus().setHorizontalRule().run()
        },
        clearFormatting: () => {
            editor.chain().focus().clearNodes().unsetAllMarks().run()
        },

        isBold: () => editor.isActive('bold'),
        isItalic: () => editor.isActive('italic'),
        isLink: () => editor.isActive('link'),
        isCode: () => editor.isActive('code'),
        isCodeBlock: () => editor.isActive('codeBlock'),
        isBulletList: () => editor.isActive('bulletList'),
        isOrderedList: () => editor.isActive('orderedList'),
        isBlockquote: () => editor.isActive('blockquote'),

        setLink: () => {
            const previous = editor.getAttributes('link').href as string | undefined
            const url = window.prompt('URL', previous ?? 'https://')
            if (url === null) return
            if (url === '') {
                editor.chain().focus().extendMarkRange('link').unsetLink().run()
                return
            }
            editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
        },
        addImage: () => {
            const url = window.prompt('Image URL')
            if (!url) return
            editor.chain().focus().setImage({ src: url }).run()
        },
    }
}

export type NoteEditorCommands = ReturnType<typeof createNoteEditorCommands>
