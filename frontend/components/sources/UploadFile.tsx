import { useRef } from 'react'
import { Plus } from 'lucide-react'

import { Button } from '../ui/button'
import { useSidebar } from '../ui/sidebar'


const ACCEPTED_SOURCE_EXTENSIONS = [
    '.pdf',
    '.docx',
    '.txt',
    '.md',
    '.png',
    '.jpg',
    '.jpeg',
] as const

type UploadFileBtn = {
    handleSelectSource: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const UploadFilePage = ({ handleSelectSource }: UploadFileBtn) => {
    const fileRef = useRef<HTMLInputElement>(null)
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'

    const handleClick = () => {
        fileRef.current?.click()
    }

    return (
        <div className={`flex flex-col gap-4 ${isCollapsed ? 'items-center' : ''}`}>
            <Button
                onClick={handleClick}
                variant="outline"
                size={isCollapsed ? 'icon' : 'default'}
                title="Add source"
                className={isCollapsed ? '' : 'w-full rounded-full font-medium'}
            >
                <Plus />
                {!isCollapsed && 'Add source'}
            </Button>
            <input type="file" accept={ACCEPTED_SOURCE_EXTENSIONS.join(',')} className="hidden" ref={fileRef} onChange={handleSelectSource} />
        </div>
    )
}

export default UploadFilePage
