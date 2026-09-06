import {
    Bold,
    Code,
    CodeXml,
    ImageIcon,
    Italic,
    Link as LinkIcon,
    List,
    ListOrdered,
    Minus,
    Quote,
    Redo2,
    RemoveFormatting,
    Undo2,
} from 'lucide-react'
import type { Editor } from '@tiptap/react'

import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'

import { applyTextStyle, getActiveTextStyle } from './noteTextStyle'
import ToolbarButton from './ToolbarButton'

type NoteToolbarProps = {
    editor: Editor;
}

function ToolbarDivider() {
    return <Separator orientation="vertical" className="mx-0.5 h-5!" />
}

export default function NoteToolbar({ editor }: NoteToolbarProps) {
    const textStyle = getActiveTextStyle(editor)

    const setLink = () => {
        const previous = editor.getAttributes('link').href as string | undefined
        const url = window.prompt('URL', previous ?? 'https://')
        if (url === null) return
        if (url === '') {
            editor.chain().focus().extendMarkRange('link').unsetLink().run()
            return
        }
        editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
    }

    const addImage = () => {
        const url = window.prompt('Image URL')
        if (!url) return
        editor.chain().focus().setImage({ src: url }).run()
    }

    return (
        <div className="flex flex-wrap items-center gap-0.5 px-3 py-2">
            <ToolbarButton
                label="Undo"
                disabled={!editor.can().undo()}
                onClick={() => editor.chain().focus().undo().run()}
            >
                <Undo2 />
            </ToolbarButton>
            <ToolbarButton
                label="Redo"
                disabled={!editor.can().redo()}
                onClick={() => editor.chain().focus().redo().run()}
            >
                <Redo2 />
            </ToolbarButton>

            <ToolbarDivider />

            <Select
                value={textStyle}
                onValueChange={(value) => {
                    if (
                        value === 'paragraph'
                        || value === 'heading1'
                        || value === 'heading2'
                        || value === 'heading3'
                    ) {
                        applyTextStyle(editor, value)
                    }
                }}
            >
                <SelectTrigger size="sm" className="h-7 min-w-28 border-0 bg-transparent shadow-none dark:bg-transparent">
                    <SelectValue />
                </SelectTrigger>
                <SelectContent align="start">
                    <SelectItem value="paragraph">Normal</SelectItem>
                    <SelectItem value="heading1">Heading 1</SelectItem>
                    <SelectItem value="heading2">Heading 2</SelectItem>
                    <SelectItem value="heading3">Heading 3</SelectItem>
                </SelectContent>
            </Select>

            <ToolbarDivider />

            <ToolbarButton
                label="Bold"
                active={editor.isActive('bold')}
                onClick={() => editor.chain().focus().toggleBold().run()}
            >
                <Bold />
            </ToolbarButton>
            <ToolbarButton
                label="Italic"
                active={editor.isActive('italic')}
                onClick={() => editor.chain().focus().toggleItalic().run()}
            >
                <Italic />
            </ToolbarButton>
            <ToolbarButton
                label="Link"
                active={editor.isActive('link')}
                onClick={setLink}
            >
                <LinkIcon />
            </ToolbarButton>
            <ToolbarButton
                label="Inline code"
                active={editor.isActive('code')}
                onClick={() => editor.chain().focus().toggleCode().run()}
            >
                <Code />
            </ToolbarButton>
            <ToolbarButton
                label="Code block"
                active={editor.isActive('codeBlock')}
                onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            >
                <CodeXml />
            </ToolbarButton>
            <ToolbarButton label="Image" onClick={addImage}>
                <ImageIcon />
            </ToolbarButton>

            <ToolbarDivider />

            <ToolbarButton
                label="Bullet list"
                active={editor.isActive('bulletList')}
                onClick={() => editor.chain().focus().toggleBulletList().run()}
            >
                <List />
            </ToolbarButton>
            <ToolbarButton
                label="Numbered list"
                active={editor.isActive('orderedList')}
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
            >
                <ListOrdered />
            </ToolbarButton>
            <ToolbarButton
                label="Quote"
                active={editor.isActive('blockquote')}
                onClick={() => editor.chain().focus().toggleBlockquote().run()}
            >
                <Quote />
            </ToolbarButton>
            <ToolbarButton
                label="Divider"
                onClick={() => editor.chain().focus().setHorizontalRule().run()}
            >
                <Minus />
            </ToolbarButton>
            <ToolbarButton
                label="Clear formatting"
                onClick={() => editor.chain().focus().clearNodes().unsetAllMarks().run()}
            >
                <RemoveFormatting />
            </ToolbarButton>
        </div>
    )
}
