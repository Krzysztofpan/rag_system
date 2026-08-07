import { useState } from 'react'
import { Dot } from 'lucide-react'
import { useNavigate } from 'react-router'

import { useEditConversationTitle } from '@/hooks/useEditConversationTitle'
import type { Conversation } from '@/types/conversation'

import { Card, CardContent, CardHeader } from '../ui/card'
import EditValueView from '../utils/EditValueView'
import ConversationOptions from './ConversationOption'

import pdfIcon from '@/src/assets/icons/pdf-icon.png'
type ConversationCardProps = {
    conversation: Conversation;
}

const ConversationCard = ({ conversation }: ConversationCardProps) => {
    const { mutate: editConversationTitle } = useEditConversationTitle()
    const navigateTo = useNavigate()
    const [editMode, setEditMode] = useState(false)


    const handleEditConversationTitle = (newTitle: string) => {
        editConversationTitle({ conversationId: conversation.id, title: newTitle })
    }

    return (
        <Card className="max-w-[320px] cursor-pointer">
            <CardContent className="w-full flex flex-col justify-between gap-4 h-full" onClick={() => void navigateTo(`/conversations/${conversation.id}`)}>
                <div className="flex justify-between">
                    <img src={pdfIcon} width={80} />
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
                                <CardHeader className="text-2xl line-clamp-2 px-0 text-wrap">{conversation.title}</CardHeader>
                            )}

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
