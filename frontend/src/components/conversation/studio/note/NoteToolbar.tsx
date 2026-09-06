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

import { createNoteEditorCommands } from './noteEditorCommands'
import ToolbarButton from './ToolbarButton'

type NoteToolbarProps = {
    editor: Editor;
}

function ToolbarDivider() {
    return <Separator orientation="vertical" className="mx-0.5 h-5!" />
}

export default function NoteToolbar({ editor }: NoteToolbarProps) {
    const commands = createNoteEditorCommands(editor)

    return (
        <div className="flex flex-wrap items-center gap-0.5 px-3 py-2">
            <ToolbarButton
                label="Undo"
                disabled={!commands.canUndo()}
                onClick={commands.undo}
            >
                <Undo2 />
            </ToolbarButton>
            <ToolbarButton
                label="Redo"
                disabled={!commands.canRedo()}
                onClick={commands.redo}
            >
                <Redo2 />
            </ToolbarButton>

            <ToolbarDivider />

            <Select
                value={commands.getTextStyle()}
                onValueChange={(value) => {
                    if (
                        value === 'paragraph'
                        || value === 'heading1'
                        || value === 'heading2'
                        || value === 'heading3'
                    ) {
                        commands.setTextStyle(value)
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
                active={commands.isBold()}
                onClick={commands.toggleBold}
            >
                <Bold />
            </ToolbarButton>
            <ToolbarButton
                label="Italic"
                active={commands.isItalic()}
                onClick={commands.toggleItalic}
            >
                <Italic />
            </ToolbarButton>
            <ToolbarButton
                label="Link"
                active={commands.isLink()}
                onClick={commands.setLink}
            >
                <LinkIcon />
            </ToolbarButton>
            <ToolbarButton
                label="Inline code"
                active={commands.isCode()}
                onClick={commands.toggleCode}
            >
                <Code />
            </ToolbarButton>
            <ToolbarButton
                label="Code block"
                active={commands.isCodeBlock()}
                onClick={commands.toggleCodeBlock}
            >
                <CodeXml />
            </ToolbarButton>
            <ToolbarButton label="Image" onClick={commands.addImage}>
                <ImageIcon />
            </ToolbarButton>

            <ToolbarDivider />

            <ToolbarButton
                label="Bullet list"
                active={commands.isBulletList()}
                onClick={commands.toggleBulletList}
            >
                <List />
            </ToolbarButton>
            <ToolbarButton
                label="Numbered list"
                active={commands.isOrderedList()}
                onClick={commands.toggleOrderedList}
            >
                <ListOrdered />
            </ToolbarButton>
            <ToolbarButton
                label="Quote"
                active={commands.isBlockquote()}
                onClick={commands.toggleBlockquote}
            >
                <Quote />
            </ToolbarButton>
            <ToolbarButton
                label="Divider"
                onClick={commands.setHorizontalRule}
            >
                <Minus />
            </ToolbarButton>
            <ToolbarButton
                label="Clear formatting"
                onClick={commands.clearFormatting}
            >
                <RemoveFormatting />
            </ToolbarButton>
        </div>
    )
}
