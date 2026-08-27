import { useState } from 'react'
import { Dot } from 'lucide-react'
import { useNavigate } from 'react-router'

import { useEditConversationTitle } from '@/hooks/useEditConversationTitle'
import { getConversationTopicStyle } from '@/lib/conversationTopic'
import type { Conversation } from '@/types/conversation'

import { Card, CardContent, CardHeader } from '../ui/card'
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip'
import EditValueView from '../utils/EditValueView'
import ConversationOptions from './ConversationOption'

type ConversationCardProps = {
    conversation: Conversation;
}

const ConversationCard = ({ conversation }: ConversationCardProps) => {
    const { mutate: editConversationTitle } = useEditConversationTitle()
    const navigateTo = useNavigate()
    const [editMode, setEditMode] = useState(false)
    const { icon, background } = getConversationTopicStyle(conversation.topic)

    const handleEditConversationTitle = (newTitle: string) => {
        editConversationTitle({ conversationId: conversation.id, title: newTitle })
    }

    const createdAt = new Date(conversation.createdAt).toLocaleDateString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    })

    return (
        <Card
            className="h-[240px] w-full cursor-pointer border-0 py-5 text-foreground hover:brightness-[0.97]"
            style={{ backgroundColor: background }}
        >
            <CardContent
                className="flex h-full w-full flex-col justify-between"
                onClick={() => void navigateTo(`/conversations/${conversation.id}`)}
            >
                <div className="flex items-start justify-between">
                    <span className="select-none text-5xl leading-none" aria-hidden>
                        {icon}
                    </span>
                    <ConversationOptions setEditMode={setEditMode} conversationId={conversation.id} />
                </div>
                <div className="flex flex-col gap-2">
                    {editMode
                        ? (
                                <div onClick={(e) => e.stopPropagation()}>
                                    <EditValueView onEdit={handleEditConversationTitle} textarea setEditMode={setEditMode} value={conversation.title} />
                                </div>
                            )
                        : (
                                <Tooltip>
                                    <TooltipTrigger delay={200} className="text-left">
                                        <CardHeader className="line-clamp-2 px-0 text-2xl font-semibold text-wrap">
                                            {conversation.title}
                                        </CardHeader>
                                    </TooltipTrigger>
                                    <TooltipContent side="bottom">{conversation.title}</TooltipContent>
                                </Tooltip>
                            )}

                    <div className="flex items-center text-sm text-muted-foreground">
                        {createdAt}
                        <Dot width={16} />
                        <span>
                            {conversation.sourceCount}
                            {' '}
                            {conversation.sourceCount === 1 ? 'source' : 'sources'}
                        </span>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}

export default ConversationCard
