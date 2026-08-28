import { useNavigate } from 'react-router';

import { Button } from '@/components/ui/button';

const NotFoundPage = () => {
    const navigate = useNavigate()

    return (
        <div className="w-full flex flex-col items-center justify-center h-[30vh] gap-10">

            <h1 className="text-4xl text-destructive">
                This page doesn't exists
            </h1>
            <Button variant="outline" onClick={() => navigate('/conversations')} className="p-6  cursor-pointer">
                Back to Conversations Page
            </Button>
        </div>
    );
}

export default NotFoundPage;
