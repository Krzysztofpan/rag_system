import axios, { type AxiosInstance } from 'axios'

import type {
    GetResourcesResponse,
    ResourceReportResponse,
    UploadResourceResponse,
} from './types'

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

    getResources = async (conversationId: string): Promise<GetResourcesResponse> => {
        const { data } = await this.client.get<GetResourcesResponse>(
            `/conversations/${conversationId}/resources`,
        )
        return data
    }

    getResourceReport = async (
        conversationId: string,
        documentId: string,
    ): Promise<ResourceReportResponse> => {
        const { data } = await this.client.get<ResourceReportResponse>(
            `/conversations/${conversationId}/resources/${documentId}/report`,
        )
        return data
    }

    uploadResource = async (
        conversationId: string,
        formData: FormData,
    ): Promise<UploadResourceResponse> => {
        const { data } = await this.client.post<UploadResourceResponse>(
            `/upload?conversation_id=${encodeURIComponent(conversationId)}`,
            formData,
        )
        return data
    }
}

export const apiService = new ApiService()
