
import { Plus } from 'lucide-react';

import { Card, CardContent } from '../ui/card';

const AddNewConversationBtn = () => {
    return (
        <Card className="max-w-[320px]">
            <CardContent className="flex flex-col gap-4 justify-center items-center h-full cursor-pointer">
                <div className="bg-blue-300/50 rounded-full p-6 text-blue-600">
                    <Plus />
                </div>
                <span className="text-xl">Create new Window</span>
            </CardContent>
        </Card>
    );
}

export default AddNewConversationBtn;
