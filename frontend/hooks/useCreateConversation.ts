import { useNavigate } from 'react-router';
import { useMutation } from '@tanstack/react-query';

import { apiService } from '@/services/api/apiService';

const useCreateConveration = () => {
    const navigateTo = useNavigate()
    return useMutation({
        mutationFn: () =>
            apiService.createConversation(),
        onSuccess: (data) => {
            void navigateTo(`/conversations/${data.conversationId}`)
        },
    });
}

export default useCreateConveration;
