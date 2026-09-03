import { Pencil, Trash2 } from 'lucide-react'

import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useDeleteSource } from '@/hooks/useDeleteSource'

import { Button } from '../../ui/button'
import { Checkbox } from '../../ui/checkbox'

type SourceActionsMenuProps = {
    sourceId: string;
    filename?: string;
    disabled?: boolean;
    showSelect?: boolean;
    onRename: () => void;
    onClose: () => void;
}

const SourceActionsMenu = ({ sourceId, filename, disabled = false, showSelect = false, onRename, onClose }: SourceActionsMenuProps) => {
    const { conversationId, selectedSources, handleToogleSelectSource: toogleSelectSource } = useConversationContext()
    const { mutate: deleteSource } = useDeleteSource(conversationId)

    return (
        <>
            {showSelect && !disabled && (
                <div className="flex items-center justify-between gap-2 px-2 py-1.5">
                    <span className="text-sm">Select</span>
                    <Checkbox checked={selectedSources.includes(sourceId)} onClick={() => toogleSelectSource(sourceId)} aria-label={filename ? `Select ${filename}` : 'Select source'} />
                </div>
            )}
            <Button
                className="justify-start"
                variant="ghost"
                onClick={() => {
                    onClose()
                    deleteSource(sourceId)
                }}
            >
                <Trash2 />
                Delete source
            </Button>
            {!disabled && (
                <Button
                    className="justify-start"
                    variant="ghost"
                    onClick={() => {
                        onClose()
                        onRename()
                    }}
                >
                    <Pencil />
                    Change name of source
                </Button>
            )}
        </>
    )
}

export default SourceActionsMenu
