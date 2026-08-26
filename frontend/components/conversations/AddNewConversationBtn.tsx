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
        <Card className="max-w-[320px]" aria-disabled={pending} onClick={handleAddConversation}>
            <CardContent className="flex flex-col gap-4 justify-center items-center h-full cursor-pointer">
                <div className="bg-blue-300/50 rounded-full p-6 text-blue-600">{pending ? <Spinner /> : <Plus />}</div>
                <span className="text-xl">{pending ? 'Creating new window' : 'Create new window'}</span>
            </CardContent>
        </Card>
    )
}

export default AddNewConversationBtn
