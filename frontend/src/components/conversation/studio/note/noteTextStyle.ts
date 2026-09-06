import type { Editor } from '@tiptap/react'

export type TextStyle = 'paragraph' | 'heading1' | 'heading2' | 'heading3'

export function getActiveTextStyle(editor: Editor): TextStyle {
    if (editor.isActive('heading', { level: 1 })) return 'heading1'
    if (editor.isActive('heading', { level: 2 })) return 'heading2'
    if (editor.isActive('heading', { level: 3 })) return 'heading3'
    return 'paragraph'
}

export function applyTextStyle(editor: Editor, style: TextStyle) {
    const chain = editor.chain().focus()
    if (style === 'paragraph') {
        chain.setParagraph().run()
        return
    }
    const level = style === 'heading1' ? 1 : style === 'heading2' ? 2 : 3
    chain.toggleHeading({ level }).run()
}
