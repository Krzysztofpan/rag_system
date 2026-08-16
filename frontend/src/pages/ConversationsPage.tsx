import ConversationsView from '@/components/conversations/ConversationsView'

const ConversationsPage = () => {
    return (
        <div className="flex flex-col gap-4 px-10 xl:px-20 2xl:px-0  2xl:mx-auto xl:max-w-[1450px] w-full py-10">
            <h1 className="text-xl">My Windows</h1>
            <div className="">
                <ConversationsView />
            </div>
        </div>
    )
}

export default ConversationsPage
