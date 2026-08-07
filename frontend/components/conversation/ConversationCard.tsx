import { Dot } from 'lucide-react';
import { useNavigate } from 'react-router';

import type { Conversation } from '@/types/conversation'

import { Card, CardContent, CardHeader } from '../ui/card'
import ConversationOptions from './ConversationOption';

import pdfIcon from '@/src/assets/icons/pdf-icon.png'
type ConversationCardProps = {
    conversation: Conversation;
}

const ConversationCard = ({ conversation }: ConversationCardProps) => {
    const navigateTo = useNavigate()

    return (
        <Card className="max-w-[320px] cursor-pointer">
            <CardContent className="w-full flex flex-col gap-10" onClick={() => void navigateTo(`/conversations/${conversation.id}`)}>
                <div className="flex justify-between">
                    <img src={pdfIcon} width={80} />
                    <ConversationOptions />
                </div>
                <div className="flex flex-col gap-2">
                    <CardHeader className="text-2xl line-clamp-2 px-0 text-wrap">
                        {conversation.conversationTitle || 'Unnamed Window wddwade dwa addw adwdwa dwad awdad adad  adadwadwadawdaadawdwaef sf'}
                    </CardHeader>
                    <div className="flex items-center text-foreground/70">
                        {new Date(conversation.updatedAt).toDateString()}
                        <Dot width={16} />
                        <span>
                            {conversation.sourceCount}
                            {' '}
                            sources
                        </span>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}

export default ConversationCard
