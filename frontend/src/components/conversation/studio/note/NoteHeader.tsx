import { ArrowLeft, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { NOTE_TITLE_MAX_CHARS } from '@/lib/note'

type NoteHeaderProps = {
    title: string;
    onTitleChange: (title: string) => void;
    onBack: () => void;
    onDelete: () => void;
    isSaving?: boolean;
    isDeleting?: boolean;
}

const NoteHeader = ({
    title,
    onTitleChange,
    onBack,
    onDelete,
    isSaving = false,
    isDeleting = false,
}: NoteHeaderProps) => {
    return (
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 px-3">
            <div className="flex min-w-0 flex-1 items-center gap-1">
                <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Back to studio"
                    disabled={isSaving || isDeleting}
                    onClick={onBack}
                    className="shrink-0 text-muted-foreground"
                >
                    <ArrowLeft />
                </Button>
                <Input
                    value={title}
                    onChange={(event) => onTitleChange(event.target.value)}
                    maxLength={NOTE_TITLE_MAX_CHARS}
                    aria-label="Note title"
                    placeholder="Note title"
                    disabled={isSaving || isDeleting}
                    className="h-auto min-w-0 flex-1 border-none bg-transparent px-1 py-1 text-xl font-semibold shadow-none ring-0 outline-none focus-visible:border-transparent focus-visible:ring-0 md:text-xl dark:bg-transparent"
                />
            </div>
            <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Delete note"
                onClick={onDelete}
                disabled={isSaving || isDeleting}
                className="shrink-0 text-muted-foreground hover:text-destructive"
            >
                <Trash2 />
            </Button>
        </header>
    )
}

export default NoteHeader
