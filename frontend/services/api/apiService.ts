import axios, { type AxiosInstance } from 'axios'

import type {
    DeleteSourceResponse,
    GetSourcesResponse,
    SourceReportResponse,
    UploadSourceResponse,
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

    getSources = async (conversationId: string): Promise<GetSourcesResponse> => {
        const { data } = await this.client.get<GetSourcesResponse>(
            `/conversations/${conversationId}/sources`,
        )
        return data
    }

    deleteSource = async (
        conversationId: string,
        documentId: string,
    ): Promise<DeleteSourceResponse> => {
        const { data } = await this.client.delete<DeleteSourceResponse>(
            `/conversations/${conversationId}/sources/${documentId}`,
        )
        return data
    }

    editSourceName = async (
        conversationId: string,
        documentId: string,
        name: string,
    ): Promise<string> => {
        const { data } = await this.client.patch<string>(
            `/conversations/${conversationId}/sources/${documentId}`,
            name,
        )

        return data
    }

    getSourceReport = async (
        conversationId: string,
        documentId: string,
    ): Promise<SourceReportResponse> => {
        const { data } = await this.client.get<SourceReportResponse>(
            `/conversations/${conversationId}/sources/${documentId}/report`,
        )
        return data
    }

    uploadSource = async (
        conversationId: string,
        formData: FormData,
    ): Promise<UploadSourceResponse> => {
        const { data } = await this.client.post<UploadSourceResponse>(
            `/upload?conversation_id=${encodeURIComponent(conversationId)}`,
            formData,
        )
        return data
    }
}

export const apiService = new ApiService()
