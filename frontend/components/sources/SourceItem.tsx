import { useState } from 'react'

import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useEditSourceName } from '@/hooks/useEditSourceName'
import { cn } from '@/lib/utils'
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
    const { conversationId } = useConversationContext()

    const { mutate: editSourceName } = useEditSourceName(conversationId)
    const [editMode, setEditMode] = useState(false)

    const isCollapsed = state === 'collapsed'
    const isPending = status === 'pending' || status === 'processing'
    const isFailed = status === 'failed'
    const iconSrc = sourceIconSrc(contentType, filename)

    const handleNameChange = (newName: string) => {
        editSourceName({ documentId: source.id, name: newName })
    }

    return (
        <div
            title={error ?? undefined}
            aria-disabled={isFailed}
            className={cn('flex gap-2 items-center group p-3 py-4 rounded-lg',
                isCollapsed ? 'justify-center rounded-full p-2 aspect-square' : 'w-full justify-between',
                isPending && 'opacity-60',
                isFailed
                    ? 'cursor-not-allowed bg-destructive/10 text-destructive ring-1 ring-inset ring-destructive/20 dark:bg-destructive/20'
                    : 'cursor-pointer hover:bg-muted')}
        >
            <div className="flex min-w-0 flex-1 items-center gap-2">
                {iconSrc
                    ? (
                            <img
                                src={iconSrc}
                                width={25}
                                alt={filename}
                                className={isFailed ? 'opacity-60' : undefined}
                            />
                        )
                    : <div className="size-6.25 shrink-0 rounded bg-muted" aria-hidden />}
                {!isCollapsed
                    && (editMode && !isFailed
                        ? (
                                <EditValueView onEdit={handleNameChange} value={filename} setEditMode={setEditMode} />
                            )
                        : (
                                <div className="min-w-0 w-full">
                                    <div className={cn('truncate text-sm', isFailed && 'opacity-80')}>{filename}</div>
                                    {error && (
                                        <p className="text-xs leading-snug wrap-break-word text-destructive" role="alert">
                                            {error}
                                        </p>
                                    )}
                                </div>
                            ))}
            </div>
            {isPending ? <Spinner /> : <SourceOptions disabled={isFailed} editMode={editMode} setEditMode={setEditMode} sourceId={source.id} />}
        </div>
    )
}

export default SourceItem
