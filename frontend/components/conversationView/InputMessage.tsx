import { SendHorizonal } from 'lucide-react'

import { useConversationContext } from '@/contexts/conversation/ConversationContext'

import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'

const InputMessage = () => {
    const { selectedSources } = useConversationContext()

    return (
        <div className="flex border-2 rounded-xl items-end x-2">
            <Textarea placeholder="Start typing..." className="resize-none py-[calc((4rem-1lh)/2)] border-none focus-within:ring-0! max-h-[300px]" />
            <div className="flex gap-2 items-center">
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                    {selectedSources.length}
                    {' '}
                    sources
                </span>
                <Button variant="outline" className="rounded-full m-4 p-2 scale-120 cursor-pointer">
                    <SendHorizonal />
                </Button>
            </div>
        </div>
    )
}

export default InputMessage
