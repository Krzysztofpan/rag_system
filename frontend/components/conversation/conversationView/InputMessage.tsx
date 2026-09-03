import { type SubmitEvent, useState } from 'react'
import { SendHorizonal } from 'lucide-react'

import { useConversationContext } from '@/contexts/conversation/ConversationContext'
import { useIsMobile } from '@/hooks/use-mobile'
import { useSendMessage } from '@/hooks/useSendMessage'

import { Button } from '../../ui/button'
import { Textarea } from '../../ui/textarea'

const InputMessage = () => {
    const { selectedSources, isPendingMessage } = useConversationContext()
    const { mutate } = useSendMessage()
    const [message, setMessage] = useState('')
    const isMobile = useIsMobile()

    const handleSendMessage = (e: SubmitEvent<HTMLFormElement> | React.KeyboardEvent<HTMLTextAreaElement>) => {
        e.preventDefault()
        if (!message) return

        const text = message
        setMessage('')
        mutate({ documentIds: selectedSources, message: text }, { onError: () => setMessage((current) => current || text) })
    }

    const handleEnterSubmit = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey && !isPendingMessage) {
            e.preventDefault()
            handleSendMessage(e)
        }
    }

    return (
        <form onSubmit={handleSendMessage} className={`flex border-2 rounded-xl items-end ${isMobile ? 'flex-col' : null}`}>
            <Textarea onKeyDown={handleEnterSubmit} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Start typing..." className={`resize-none ${isMobile ? 'min-h-0 px-4 py-2' : 'py-[calc((4rem-1lh)/2)]'} border-none focus-within:ring-0! max-h-[300px]`} />
            <div className="flex gap-2 items-center">
                <span className={`${isMobile ? 'text-xs' : 'text-sm'} text-muted-foreground whitespace-nowrap `}>
                    {selectedSources.length}
                    {' '}
                    sources
                </span>
                <Button disabled={isPendingMessage || !message} variant="outline" type="submit" className={`rounded-full ${isMobile ? 'm-2 scale-110' : 'm-4 scale-120 '} p-2 cursor-pointer`}>
                    <SendHorizonal />
                </Button>
            </div>
        </form>
    )
}

export default InputMessage
