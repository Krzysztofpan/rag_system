import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'

import { cn } from '@/lib/utils'

import { Button } from '../../ui/button'
import { ACCEPTED_SOURCE_EXTENSIONS, ACCEPTED_SOURCE_FORMATS_LABEL, isAcceptedSourceFile } from './acceptedSourceFiles'

type FileDropzoneProps = {
    onFile: (file: File) => void;
}

const FileDropzone = ({ onFile }: FileDropzoneProps) => {
    const fileRef = useRef<HTMLInputElement>(null)
    const dragCountRef = useRef(0)
    const [isDragging, setIsDragging] = useState(false)
    const [fileError, setFileError] = useState<string | null>(null)

    const handlePickFile = () => {
        fileRef.current?.click()
    }

    const addFile = (file: File | undefined) => {
        if (!file) return
        if (!isAcceptedSourceFile(file)) {
            setFileError('This file type is not supported')
            return
        }
        onFile(file)
    }

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        e.target.value = ''
        addFile(file)
    }

    const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        dragCountRef.current += 1
        setIsDragging(true)
        setFileError(null)
    }

    const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        dragCountRef.current -= 1
        if (dragCountRef.current <= 0) {
            dragCountRef.current = 0
            setIsDragging(false)
        }
    }

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = 'copy'
    }

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault()
        dragCountRef.current = 0
        setIsDragging(false)
        addFile(e.dataTransfer.files[0])
    }

    return (
        <div
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className={cn(
                'flex min-h-52 flex-col rounded-2xl border border-dashed p-5 transition-colors',
                isDragging ? 'border-sky-500 bg-sky-500/10' : 'border-muted-foreground/35',
            )}
        >
            <div className="flex flex-1 flex-col items-center justify-center gap-1 py-8 text-center">
                <p className="text-base">or drop files</p>
                <p className="text-sm text-muted-foreground">{ACCEPTED_SOURCE_FORMATS_LABEL}</p>
                {fileError && <p className="mt-2 text-sm text-destructive">{fileError}</p>}
            </div>
            <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
                <Button type="button" variant="secondary" className="rounded-full" onClick={handlePickFile}>
                    <Upload />
                    Upload files
                </Button>
            </div>
            <input type="file" accept={ACCEPTED_SOURCE_EXTENSIONS.join(',')} className="hidden" ref={fileRef} onChange={handleFileInputChange} />
        </div>
    )
}

export default FileDropzone
