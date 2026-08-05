import { type Dispatch, type SetStateAction, useEffect, useRef } from 'react';

import { useEditSourceName } from '@/hooks/useEditSourceName';

import { Input } from './ui/input';

type SourceNameEditViewProps = {
    conversationId: string;
    sourceId: string;
    filename: string;
    setEditMode: Dispatch<SetStateAction<boolean>>;
}

const SourceNameEditView = ({ conversationId, sourceId, filename, setEditMode }: SourceNameEditViewProps) => {
    const { mutate: editSourceName } = useEditSourceName(conversationId)
    const inputRef = useRef<null | HTMLInputElement>(null)

    useEffect(() => {
        if (inputRef.current) {
            inputRef.current.focus()
        }
    }, [])

    return (
        <form
            onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.currentTarget);
                const name = formData.get('name') as string
                editSourceName({ documentId: sourceId, name })
                setEditMode(false)
            }}
            className="w-full flex items-center p-0 m-0 h-5"
        >
            <Input
                name="name"
                id="name"
                ref={inputRef}
                maxLength={50}
                defaultValue={filename}
                onBlur={() => setEditMode(false)}
                className="outline-none text-muted w-full bg-muted-foreground border-none shadow-none ring-0 focus:outline-0 focus-within:border-0! focus-within:ring-0!"
            />
        </form>
    );
}

export default SourceNameEditView;
