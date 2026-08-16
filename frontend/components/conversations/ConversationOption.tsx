import { type Dispatch, type SetStateAction, useState } from 'react'
import { EllipsisVertical, Pencil, Trash2 } from 'lucide-react'

import useDeleteConversation from '@/hooks/useDeleteConversation'

import { Button } from '../ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover'

type ConversationOptionsProps = {
    setEditMode: Dispatch<SetStateAction<boolean>>;
    conversationId: string;
}

const ConversationOptions = ({ setEditMode, conversationId }: ConversationOptionsProps) => {
    const [isOpen, setIsOpen] = useState(false)
    const { mutate: deleteConversation } = useDeleteConversation()

    const handleNameChange = () => {
        setEditMode(true)
        setIsOpen(false)
    }

    return (
        <div className="gap-2 items-center" onClick={(e) => { e.stopPropagation() }}>
            <Popover onOpenChange={setIsOpen}>
                <PopoverTrigger className={` group-hover:block p-0 m-0 flex justify-center items-center cursor-pointer`}>
                    <EllipsisVertical size={18} />
                </PopoverTrigger>
                <PopoverContent side="bottom" align="start" className={`${isOpen ? 'flex' : 'hidden'}  flex-col  gap-0 p-0`}>
                    <Button className="p-5 py-6 text-base flex gap-2 justify-start items-center cursor-pointer" variant="ghost" onClick={() => deleteConversation(conversationId)}>
                        <Trash2 className="scale-125" />
                        Delete Window
                    </Button>
                    <Button
                        className="p-5 text-base flex gap-2 justify-start items-center cursor-pointer"
                        variant="ghost"
                        onClick={handleNameChange}
                    >
                        <Pencil className="scale-125" />
                        Change name of Window
                    </Button>
                </PopoverContent>
            </Popover>
        </div>
    );
}

export default ConversationOptions;
