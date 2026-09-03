import { type SubmitEvent, useState } from 'react'
import { Search } from 'lucide-react'

import { Button } from '@/components/ui/button'

import youtubeIcon from '@/src/assets/icons/youtube-icon.png'

type YoutubeUrlFormProps = {
    onAdd: (url: string) => void;
}

const YoutubeUrlForm = ({ onAdd }: YoutubeUrlFormProps) => {
    const [url, setUrl] = useState('')

    const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
        e.preventDefault()
        const next = url.trim()
        if (!next) return
        onAdd(next)
    }

    return (
        <form className="relative flex min-h-28 flex-col justify-between gap-6 rounded-2xl border border-sky-500/80 bg-background/40 p-3" onSubmit={handleSubmit}>
            <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Paste a YouTube link"
                aria-label="YouTube URL"
                autoFocus
                className="w-full bg-transparent px-2 pt-1 text-sm outline-none placeholder:text-muted-foreground"
            />
            <div className="flex items-center justify-between gap-2">
                <div className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs font-medium">
                    <img src={youtubeIcon} alt="" width={14} height={14} className="size-3.5" />
                    YouTube
                </div>
                <Button type="submit" size="icon-sm" variant="ghost" disabled={!url.trim()} aria-label="Add YouTube video">
                    <Search />
                </Button>
            </div>
        </form>
    )
}

export default YoutubeUrlForm
