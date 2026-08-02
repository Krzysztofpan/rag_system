import axios, { type AxiosInstance } from 'axios'

import type { UploadResourceResponse } from '@/types/upload'

class ApiService {
    private apiHost = import.meta.env.VITE_BACKEND_URL
    private client: AxiosInstance

    constructor() {
        this.client = this.constructClient()
    }

    private constructClient = () => {
        return axios.create({
            baseURL: this.apiHost,
            /* headers: {
                Authorization: this.token,
            }, */
        })
    }

    uploadResource = async (conversationId: string, file: File): Promise<UploadResourceResponse> => {
        const formData = new FormData()
        formData.append('file', file)

        const { data } = await this.client.post<UploadResourceResponse>(
            `/upload?conversation_id=${encodeURIComponent(conversationId)}`,
            formData,
        )
        return data
    }
}

export const apiService = new ApiService()
