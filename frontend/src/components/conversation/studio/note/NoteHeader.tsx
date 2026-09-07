import { ArrowLeft, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'

type NoteHeaderProps = {
    title: string;
    onBack?: () => void;
    onDelete?: () => void;
}

const NoteHeader = ({ title, onBack, onDelete }: NoteHeaderProps) => {
    return (
        <header className="flex h-12 shrink-0 items-center justify-between gap-3 px-3">
            <div className="flex min-w-0 items-center gap-1">
                {onBack && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        aria-label="Back to studio"
                        onClick={onBack}
                        className="shrink-0 text-muted-foreground"
                    >
                        <ArrowLeft />
                    </Button>
                )}
                <h2 className="truncate text-sm font-medium">{title}</h2>
            </div>
            <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Delete note"
                onClick={onDelete}
                className="shrink-0 text-muted-foreground hover:text-destructive"
            >
                <Trash2 />
            </Button>
        </header>
    )
}

export default NoteHeader
