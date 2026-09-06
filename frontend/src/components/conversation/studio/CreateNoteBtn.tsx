import { NotepadText } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useSidebar } from '@/components/ui/sidebar'

type CreateNoteBtnProps = {
    onOpenNote: () => void;
}

const CreateNoteBtn = ({ onOpenNote }: CreateNoteBtnProps) => {
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'

    return (
        <Button
            type="button"
            onClick={onOpenNote}
            className={`${isCollapsed ? 'aspect-square px-2 scale-110 bottom-2' : 'space-x-2 px-7 py-5 bottom-0 '} rounded-2xl cursor-pointer absolute -translate-1/2 left-1/2`}
        >
            <NotepadText />
            {!isCollapsed && <span>Add note</span>}
        </Button>
    )
}

export default CreateNoteBtn
