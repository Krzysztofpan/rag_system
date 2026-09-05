import { NotepadText } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useSidebar } from '@/components/ui/sidebar';

const CreateNoteBtn = () => {
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'


    return (
        <Button className={`${isCollapsed ? 'aspect-square rounded-2xl px-2 scale-110 bottom-2' : 'space-x-2 px-7 py-5 bottom-0 '}  cursor-pointer absolute -translate-1/2 left-1/2  rounded-2xl `}>
            <NotepadText />
            {!isCollapsed && <span>Dodaj notatkę</span>}
        </Button>
    );
}

export default CreateNoteBtn;
