import { useState } from 'react'

import ConversationsPageHeader from '@/components/conversations/ConversationsPageHeader'
import ConversationsView from '@/components/conversations/ConversationsView'

import { items } from './ConversationPage.const'

const ConversationsPage = () => {
    const [sortMethodIndex, setSortMethodIndex] = useState<number | null>(0)
    const [searchValue, setSearchValue] = useState('')

    return (
        <div className="flex flex-col gap-8 xl:max-w-[1450px] xl:px-20 2xl:px-0  2xl:mx-auto w-full py-10 px-10">
            <title>Folio - Conversations</title>
            <ConversationsPageHeader searchValue={searchValue} setSearchValue={setSearchValue} setSortMethodIndex={setSortMethodIndex} sortMethodIndex={sortMethodIndex} />
            <div className="flex flex-col gap-4">
                <h1 className="text-xl">My Conversations</h1>
                <div className="">
                    <ConversationsView searchValue={searchValue ?? null} sortMethod={items[sortMethodIndex ?? 0].method} />
                </div>
            </div>
        </div>
    )
}

export default ConversationsPage
