import { SendHorizonal } from 'lucide-react'

import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'

const InputMessage = () => {
    return (
        <div className="flex border-2 rounded-xl items-end x-2">
            <Textarea placeholder="Start typing..." className="resize-none py-[calc((4rem-1lh)/2)] border-none focus-within:ring-0! max-h-[300px]" />
            <Button variant="outline" className="rounded-full m-4 p-2 scale-120 cursor-pointer">
                <SendHorizonal />
            </Button>
        </div>
    )
}

export default InputMessage
