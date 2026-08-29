import { useState } from 'react'

import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useEditSourceName } from '@/hooks/useEditSourceName'
import { sourceIconSrc } from '@/types/IconsMap'
import type { Source } from '@/types/source'

import { useSidebar } from '../ui/sidebar'
import { Spinner } from '../ui/spinner'
import EditValueView from '../utils/EditValueView'
import SourceOptions from './SourceOptions'

type SourceItemProps = {
    source: Source;
}

const SourceItem = ({ source }: SourceItemProps) => {
    const { filename, contentType, status, error } = source
    const { state } = useSidebar()
    const {
        conversationId,
    } = useConversationContext()

    const { mutate: editSourceName } = useEditSourceName(conversationId)
    const [editMode, setEditMode] = useState(false)

    const isCollapsed = state === 'collapsed'
    const isPending = status === 'pending' || status === 'processing'
    const iconSrc = sourceIconSrc(contentType, filename)

    const handleNameChange = (newName: string) => {
        editSourceName({ documentId: source.id, name: newName })
    }

    return (
        <div
            title={error ?? undefined}
            className={`flex gap-2 items-center group hover:bg-muted p-3 py-4 rounded-lg cursor-pointer
        ${isCollapsed ? 'justify-center' : 'w-full justify-between'} ${isPending ? 'opacity-60' : ''}
        `}
        >
            <div className="flex min-w-0 w-full items-center gap-2">
                {iconSrc
                    ? <img src={iconSrc} width={25} alt={filename} className={status === 'failed' ? 'opacity-60' : undefined} />
                    : <div className="size-6.25 shrink-0 rounded bg-muted" aria-hidden />}
                {!isCollapsed && (editMode
                    ? (
                            <EditValueView
                                onEdit={handleNameChange}
                                value={filename}
                                setEditMode={setEditMode}
                            />
                        )
                    : (
                            <div className="min-w-0 w-full">
                                <div className={`truncate text-sm ${status === 'failed' ? 'opacity-60' : ''}`}>{filename}</div>
                                {error && (
                                    <p className="line-clamp-2 text-xs leading-snug text-destructive" role="alert">
                                        {error}
                                    </p>
                                )}
                            </div>
                        ))}
            </div>
            {isPending
                ? <Spinner />
                : (
                        <SourceOptions
                            editMode={editMode}
                            setEditMode={setEditMode}
                            sourceId={source.id}
                        />
                    )}
        </div>
    )
}

export default SourceItem
