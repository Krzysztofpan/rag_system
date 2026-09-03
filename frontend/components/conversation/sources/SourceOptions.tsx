import { type Dispatch, type SetStateAction, useState } from 'react'
import { EllipsisVertical } from 'lucide-react'

import { Checkbox } from '@/components/ui/checkbox'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useSidebar } from '@/components/ui/sidebar'
import { useConversationContext } from '@/contexts/conversation/ConversationContext'

import SourceActionsMenu from './SourceActionsMenu'

type SourceOptionsProps = {
    disabled?: boolean;
    editMode: boolean;
    setEditMode: Dispatch<SetStateAction<boolean>>;
    sourceId: string;
}

const SourceOptions = ({ disabled = false, editMode, setEditMode, sourceId }: SourceOptionsProps) => {
    const [isOpen, setIsOpen] = useState(false)
    const { selectedSources, handleToogleSelectSource: toogleSelectSource } = useConversationContext()
    const { state } = useSidebar()

    const isCollapsed = state === 'collapsed'

    if (isCollapsed || editMode) {
        return null
    }

    return (
        <div className="flex gap-2 items-center">
            <Popover open={isOpen} onOpenChange={setIsOpen}>
                <PopoverTrigger className={`${isOpen || disabled ? 'block' : 'hidden'} group-hover:block p-0 m-0 flex justify-center items-center cursor-pointer`}>
                    <EllipsisVertical size={18} />
                </PopoverTrigger>
                <PopoverContent side="bottom" align="start" className="w-56 gap-0 p-1">
                    <SourceActionsMenu sourceId={sourceId} disabled={disabled} onClose={() => setIsOpen(false)} onRename={() => setEditMode(true)} />
                </PopoverContent>
            </Popover>
            {!disabled && <Checkbox checked={selectedSources.includes(sourceId)} onClick={() => toogleSelectSource(sourceId)} />}
        </div>
    )
}

export default SourceOptions
