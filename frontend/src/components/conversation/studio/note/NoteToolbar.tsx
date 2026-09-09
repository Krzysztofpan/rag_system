import { Fragment } from 'react'
import type { Editor } from '@tiptap/react'

import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'

import {
    createNoteEditorCommands,
    formatGroups,
    historyItems,
    type ToolbarItem,
} from './noteEditorCommands'
import ToolbarButton from './ToolbarButton'

type NoteToolbarProps = {
    editor: Editor;
}

function ToolbarDivider() {
    return <Separator orientation="vertical" className="mx-0.5 h-5!" />
}

function ToolbarButtons({ items }: { items: ToolbarItem[] }) {
    return items.map(({ label, icon: Icon, onClick, active, disabled }) => (
        <ToolbarButton
            key={label}
            label={label}
            active={active}
            disabled={disabled}
            onClick={onClick}
        >
            <Icon />
        </ToolbarButton>
    ))
}

export default function NoteToolbar({ editor }: NoteToolbarProps) {
    const commands = createNoteEditorCommands(editor)

    return (
        <div className="flex flex-wrap items-center gap-0.5 px-3 py-2">
            <ToolbarButtons items={historyItems(commands)} />

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

            {formatGroups(commands).map((group) => (
                <Fragment key={group[0].label}>
                    <ToolbarDivider />
                    <ToolbarButtons items={group} />
                </Fragment>
            ))}
        </div>
    )
}
