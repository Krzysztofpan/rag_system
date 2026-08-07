import { type Dispatch, type SetStateAction } from 'react'

import { Input } from '../ui/input'
import { Textarea } from '../ui/textarea'

type SourceNameEditViewProps = {
    onEdit: (newValue: string) => void;
    value: string;
    setEditMode: Dispatch<SetStateAction<boolean>>;
    maxLength?: number;
    textarea?: boolean;
}

const EditValueView = ({ onEdit, value, setEditMode, textarea, maxLength = 50 }: SourceNameEditViewProps) => {
    return (
        <form
            onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.currentTarget)
                const newValue = formData.get('value') as string
                onEdit(newValue)
                setEditMode(false)
            }}
            className={`w-full flex items-center p-0 m-0 ${!textarea && 'h-5'}`}
        >
            {textarea
                ? (
                        <Textarea
                            name="value"
                            id="value"
                            autoFocus
                            maxLength={maxLength}
                            defaultValue={value}
                            onBlur={() => setEditMode(false)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault()
                                    e.currentTarget.form?.requestSubmit()
                                }
                            }}
                            className="text-2xl! resize-none outline-none text-muted w-full bg-muted-foreground border-none shadow-none ring-0 focus:outline-0 focus-within:border-0! focus-within:ring-0!"
                        />
                    )
                : (
                        <Input
                            name="value"
                            id="value"
                            autoFocus
                            maxLength={maxLength}
                            defaultValue={value}
                            onBlur={() => setEditMode(false)}
                            className="outline-none text-muted w-full bg-muted-foreground border-none shadow-none ring-0 focus:outline-0 focus-within:border-0! focus-within:ring-0!"
                        />
                    )}
        </form>
    )
}

export default EditValueView
