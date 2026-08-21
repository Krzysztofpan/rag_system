import { useMutation } from '@tanstack/react-query'

import { useConversationContext } from '@/contexts/conversation/ConversationContext';

type useSendMessageFncProps = {
    documentIds: string[];
    message: string;
}

export const useSendMessage = () => {
    const { sendMessage } = useConversationContext()
    return useMutation({
        mutationFn: ({ documentIds, message }: useSendMessageFncProps) =>
            sendMessage({ documentIds, message }),
    })
}
