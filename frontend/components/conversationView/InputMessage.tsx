import { type SubmitEvent, useState } from 'react'
import { SendHorizonal } from 'lucide-react'

import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useSendMessage } from '@/hooks/useSendMessage'

import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'

const InputMessage = () => {
    const { selectedSources, isPendingMessage } = useConversationContext()
    const { mutate } = useSendMessage()
    const [message, setMessage] = useState('')

    const handleSendMessage = (e: SubmitEvent<HTMLFormElement> | React.KeyboardEvent<HTMLTextAreaElement>) => {
        e.preventDefault()
        if (!message) return;

        mutate({ documentIds: selectedSources, message })
        setMessage('')
    }

    const handleEnterSubmit = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey && !isPendingMessage) {
            e.preventDefault()
            handleSendMessage(e)
        }
    }

    return (
        <form onSubmit={handleSendMessage} className="flex border-2 rounded-xl items-end x-2">
            <Textarea onKeyDown={handleEnterSubmit} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Start typing..." className="resize-none py-[calc((4rem-1lh)/2)] border-none focus-within:ring-0! max-h-[300px]" />
            <div className="flex gap-2 items-center">
                <span className="text-sm text-muted-foreground whitespace-nowrap">
                    {selectedSources.length}
                    {' '}
                    sources
                </span>
                <Button disabled={isPendingMessage || !message} variant="outline" type="submit" className="rounded-full m-4 p-2 scale-120 cursor-pointer">
                    <SendHorizonal />
                </Button>
            </div>
        </form>
    )
}

export default InputMessage
