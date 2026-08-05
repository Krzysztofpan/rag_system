import { useState } from 'react'

import { IconsMap } from '@/types/IconsMap'
import type { Source } from '@/types/source'

import { useSidebar } from '../ui/sidebar'
import { Spinner } from '../ui/spinner'
import SourceNameEditView from './SourceNameEditView'
import SourceOptions from './SourceOptions'

type SourceItemProps = {
    source: Source;
    conversationId: string;
}

const SourceItem = ({ source, conversationId }: SourceItemProps) => {
    const { filename, contentType, status, error } = source
    const { state } = useSidebar()

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
                ? <Spinner />
                : (
                        <SourceOptions
                            conversationId={conversationId}
                            editMode={editMode}
                            setEditMode={setEditMode}
                            sourceId={source.id}
                        />
                    )}
        </div>
    )
}

export default SourceItem
