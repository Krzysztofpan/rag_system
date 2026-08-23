import { useRef, useState } from 'react'
import { FileUp, Plus } from 'lucide-react'

import { Button } from '../ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu'
import { Input } from '../ui/input'
import { useSidebar } from '../ui/sidebar'

import youtubeIcon from '@/src/assets/icons/youtube-icon.png'

const ACCEPTED_SOURCE_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md', '.png', '.jpg', '.jpeg'] as const

type UploadFileBtn = {
    handleSelectSource: (e: React.ChangeEvent<HTMLInputElement>) => void;
    handleAddYoutubeUrl: (url: string) => void;
}

const UploadFilePage = ({ handleSelectSource, handleAddYoutubeUrl }: UploadFileBtn) => {
    const fileRef = useRef<HTMLInputElement>(null)
    const { state } = useSidebar()
    const isCollapsed = state === 'collapsed'
    const [urlOpen, setUrlOpen] = useState(false)
    const [url, setUrl] = useState('')

    const handlePickFile = () => {
        setUrlOpen(false)
        fileRef.current?.click()
    }

    const handlePickYoutube = () => {
        if (isCollapsed) {
            const next = window.prompt('YouTube URL')
            if (next?.trim()) {
                handleAddYoutubeUrl(next.trim())
            }
            return
        }
        setUrlOpen(true)
    }

    const handleSubmitUrl = (e: React.SubmitEvent<HTMLFormElement>) => {
        e.preventDefault()
        const next = url.trim()
        if (!next) return
        handleAddYoutubeUrl(next)
        setUrl('')
        setUrlOpen(false)
    }

    return (
        <div className={`flex flex-col gap-2 ${isCollapsed ? 'items-center' : ''}`}>
            <DropdownMenu>
                <DropdownMenuTrigger render={<Button variant="outline" size={isCollapsed ? 'icon' : 'default'} title="Add source" className={isCollapsed ? '' : 'w-full rounded-full font-medium'} />}>
                    <Plus />
                    {!isCollapsed && 'Add source'}
                </DropdownMenuTrigger>
                <DropdownMenuContent className="min-w-40">
                    <DropdownMenuItem onClick={handlePickFile}>
                        <FileUp />
                        Upload file
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={handlePickYoutube}>
                        <img src={youtubeIcon} alt="" width={16} height={16} className="size-4" />
                        YouTube URL
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
            <input type="file" accept={ACCEPTED_SOURCE_EXTENSIONS.join(',')} className="hidden" ref={fileRef} onChange={handleSelectSource} />
            {urlOpen && !isCollapsed && (
                <form className="flex flex-col gap-2" onSubmit={handleSubmitUrl}>
                    <Input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=..." aria-label="YouTube URL" autoFocus />
                    <Button type="submit" size="sm" className="w-full">
                        Add video
                    </Button>
                </form>
            )}
        </div>
    )
}

export default UploadFilePage
