import { useState } from 'react'
import { EllipsisVertical, Pencil, Trash2 } from 'lucide-react'

import { useDeleteSource } from '@/hooks/useDeleteSource'
import { IconsMap } from '@/types/IconsMap'
import type { Source } from '@/types/source'

import { Button } from './ui/button'
import { Checkbox } from './ui/checkbox'
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover'
import { useSidebar } from './ui/sidebar'
import { Spinner } from './ui/spinner'
import SourceNameEditView from './SourceNameEditView'

type SourceItemProps = {
    source: Source;
    conversationId: string;
}

const SourceItem = ({ source, conversationId }: SourceItemProps) => {
    const { filename, contentType, status, error } = source
    const { state } = useSidebar()
    const [isOpen, setIsOpen] = useState(false)
    const { mutate: deleteSource } = useDeleteSource(conversationId)
    const [editMode, setEditMode] = useState(false)

    const isCollapsed = state === 'collapsed'
    const isPending = status === 'pending' || status === 'processing'
    const iconSrc = contentType ? IconsMap[contentType] : undefined

    return (
        <div
            title={error ?? undefined}
            className={`flex gap-2 items-center group hover:bg-muted p-3 py-4 rounded-lg cursor-pointer
        ${isCollapsed ? 'justify-center' : 'w-full justify-between'} ${status === 'failed' || isPending ? 'opacity-60' : ''}  
        `}
        >
            <div className="flex gap-2 items-center min-w-0 w-full">
                {iconSrc ? <img src={iconSrc} width={25} alt={filename} /> : <div className="size-6.25 shrink-0 rounded bg-muted" aria-hidden />}
                {!isCollapsed && editMode
                    ? (
                            <SourceNameEditView
                                filename={filename}
                                conversationId={conversationId}
                                sourceId={source.id}
                                setEditMode={setEditMode}
                            />
                        )
                    : <div className="flex items-center text-sm truncate w-full">{filename}</div>}
            </div>
            {isPending
                ? (
                        <Spinner />
                    )
                : (
                        <div className={`${isCollapsed || editMode ? 'hidden' : 'flex'} gap-2 items-center`}>
                            <Popover onOpenChange={setIsOpen}>
                                <PopoverTrigger className={`${isOpen ? 'block' : 'hidden'} group-hover:block p-0 m-0 flex justify-center items-center cursor-pointer`}>
                                    <EllipsisVertical size={18} />
                                </PopoverTrigger>
                                <PopoverContent side="bottom" align="start" className={`${isOpen ? 'flex' : 'hidden'} w-56 flex-col  gap-0 p-0`}>
                                    <Button className="p-5 flex gap-2 justify-start cursor-pointer" variant="ghost" onClick={() => deleteSource(source.id)}>
                                        <Trash2 />
                                        Delete source
                                    </Button>
                                    <Button
                                        className="p-5 flex gap-2 justify-start cursor-pointer"
                                        variant="ghost"
                                        onClick={() => {
                                            setEditMode(true)
                                            setIsOpen(false)
                                        }}
                                    >
                                        <Pencil />
                                        Change name of source
                                    </Button>
                                </PopoverContent>
                            </Popover>
                            {!isCollapsed && !editMode && <Checkbox />}
                        </div>
                    )}
        </div>
    )
}

export default SourceItem
