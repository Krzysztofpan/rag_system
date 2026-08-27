import { useTransition } from 'react'
import { Plus } from 'lucide-react'

import useCreateConveration from '@/hooks/useCreateConversation'

import { Card, CardContent } from '../ui/card'
import { Spinner } from '../ui/spinner'

const AddNewConversationBtn = () => {
    const { mutate: createConversation } = useCreateConveration()
    const [pending, startTransition] = useTransition()

    const handleAddConversation = () => {
        startTransition(() => {
            createConversation()

            return
        })
    }

    return (
        <Card className="h-[240px] w-full" aria-disabled={pending} onClick={handleAddConversation}>
            <CardContent className="flex h-full cursor-pointer flex-col items-center justify-center gap-4">
                <div className="rounded-full bg-blue-300/50 p-6 text-blue-600">{pending ? <Spinner /> : <Plus size={28} />}</div>
                <span className="text-xl">{pending ? 'Creating new Conversation' : 'Create new Conversation'}</span>
            </CardContent>
        </Card>
    )
}

export default AddNewConversationBtn
