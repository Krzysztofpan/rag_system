import { type Dispatch, type SetStateAction, useState } from 'react'
import { EllipsisVertical, Pencil, Trash2 } from 'lucide-react'

import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useDeleteSource } from '@/hooks/useDeleteSource'

import { Button } from '../ui/button'
import { Checkbox } from '../ui/checkbox'
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover'
import { useSidebar } from '../ui/sidebar'

type SourceOptionsProps = {
    disabled?: boolean;
    editMode: boolean;
    setEditMode: Dispatch<SetStateAction<boolean>>;
    sourceId: string;
}

const SourceOptions = ({ disabled = false, editMode, setEditMode, sourceId }: SourceOptionsProps) => {
    const [isOpen, setIsOpen] = useState(false)
    const {
        conversationId,
        selectedSources,
        handleToogleSelectSource: toogleSelectSource,
    } = useConversationContext()
    const { mutate: deleteSource } = useDeleteSource(conversationId)
    const { state } = useSidebar()

    const isCollapsed = state === 'collapsed'

    return (
        <div className={`${isCollapsed || editMode ? 'hidden' : 'flex'} gap-2 items-center`}>
            <Popover onOpenChange={setIsOpen}>
                <PopoverTrigger className={`${isOpen || disabled ? 'block' : 'hidden'} group-hover:block p-0 m-0 flex justify-center items-center cursor-pointer`}>
                    <EllipsisVertical size={18} />
                </PopoverTrigger>
                <PopoverContent side="bottom" align="start" className={`${isOpen ? 'flex' : 'hidden'} w-56 flex-col  gap-0 p-0`}>
                    <Button className="p-5 flex gap-2 justify-start cursor-pointer" variant="ghost" onClick={() => deleteSource(sourceId)}>
                        <Trash2 />
                        Delete source
                    </Button>
                    {!disabled && (
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
                    )}
                </PopoverContent>
            </Popover>
            {!isCollapsed && !editMode && !disabled && (
                <Checkbox
                    checked={selectedSources.includes(sourceId)}
                    onClick={() => toogleSelectSource(sourceId)}
                />
            )}
        </div>
    );
}

export default SourceOptions;
