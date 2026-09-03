import { useState } from 'react'

import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useEditSourceName } from '@/hooks/useEditSourceName'
import { cn } from '@/lib/utils'

import { Popover, PopoverContent, PopoverTrigger } from '../../ui/popover'
import { Spinner } from '../../ui/spinner'
import { Tooltip, TooltipContent, TooltipTrigger } from '../../ui/tooltip'
import RenameSourceDialog from './RenameSourceDialog'
import SourceActionsMenu from './SourceActionsMenu'

type CollapsedSourceMenuProps = {
    sourceId: string;
    filename: string;
    iconSrc: string | undefined;
    isFailed: boolean;
    isPending: boolean;
}

const CollapsedSourceMenu = ({
    sourceId,
    filename,
    iconSrc,
    isFailed,
    isPending,
}: CollapsedSourceMenuProps) => {
    const { conversationId } = useConversationContext()
    const { mutate: editSourceName } = useEditSourceName(conversationId)

    const [isPopoverOpen, setIsPopoverOpen] = useState(false)
    const [isRenameDialogOpen, setIsRenameDialogOpen] = useState(false)

    const sourceIcon = (
        <img
            src={iconSrc}
            width={25}
            alt={filename}
            className={cn((isFailed || isPending) && 'opacity-60')}
        />
    )

    if (isPending) {
        return (
            <div className="relative flex size-6.25 shrink-0 items-center justify-center">
                {sourceIcon}
                <Spinner className="absolute size-4" />
            </div>
        )
    }

    return (
        <>
            <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
                <Tooltip disabled={isPopoverOpen}>
                    <TooltipTrigger delay={200} render={<PopoverTrigger className="flex shrink-0 cursor-pointer" />}>
                        {sourceIcon}
                    </TooltipTrigger>
                    <TooltipContent side="right">{filename}</TooltipContent>
                </Tooltip>
                <PopoverContent side="right" align="start" className="w-56 gap-0 p-1">
                    <SourceActionsMenu
                        sourceId={sourceId}
                        filename={filename}
                        disabled={isFailed}
                        showSelect
                        onClose={() => setIsPopoverOpen(false)}
                        onRename={() => setIsRenameDialogOpen(true)}
                    />
                </PopoverContent>
            </Popover>
            <RenameSourceDialog
                filename={filename}
                open={isRenameDialogOpen}
                onOpenChange={setIsRenameDialogOpen}
                onSave={(name) => editSourceName({ documentId: sourceId, name })}
            />
        </>
    )
}

export default CollapsedSourceMenu
