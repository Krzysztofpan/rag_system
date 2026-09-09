import {
    Bold,
    Code,
    CodeXml,
    ImageIcon,
    Italic,
    Link as LinkIcon,
    List,
    ListOrdered,
    type LucideIcon,
    Minus,
    Quote,
    Redo2,
    RemoveFormatting,
    Undo2,
} from 'lucide-react'
import type { Editor } from '@tiptap/react'

import { applyTextStyle, getActiveTextStyle, type TextStyle } from './noteTextStyle'

export type ToolbarItem = {
    label: string;
    icon: LucideIcon;
    onClick: () => void;
    active?: boolean;
    disabled?: boolean;
}

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

export function historyItems(commands: NoteEditorCommands): ToolbarItem[] {
    return [
        { label: 'Undo', icon: Undo2, onClick: commands.undo, disabled: !commands.canUndo() },
        { label: 'Redo', icon: Redo2, onClick: commands.redo, disabled: !commands.canRedo() },
    ]
}

export function formatGroups(commands: NoteEditorCommands): ToolbarItem[][] {
    return [
        [
            { label: 'Bold', icon: Bold, onClick: commands.toggleBold, active: commands.isBold() },
            { label: 'Italic', icon: Italic, onClick: commands.toggleItalic, active: commands.isItalic() },
            { label: 'Link', icon: LinkIcon, onClick: commands.setLink, active: commands.isLink() },
            { label: 'Inline code', icon: Code, onClick: commands.toggleCode, active: commands.isCode() },
            { label: 'Code block', icon: CodeXml, onClick: commands.toggleCodeBlock, active: commands.isCodeBlock() },
            { label: 'Image', icon: ImageIcon, onClick: commands.addImage },
        ],
        [
            { label: 'Bullet list', icon: List, onClick: commands.toggleBulletList, active: commands.isBulletList() },
            { label: 'Numbered list', icon: ListOrdered, onClick: commands.toggleOrderedList, active: commands.isOrderedList() },
            { label: 'Quote', icon: Quote, onClick: commands.toggleBlockquote, active: commands.isBlockquote() },
            { label: 'Divider', icon: Minus, onClick: commands.setHorizontalRule },
            { label: 'Clear formatting', icon: RemoveFormatting, onClick: commands.clearFormatting },
        ],
    ]
}
