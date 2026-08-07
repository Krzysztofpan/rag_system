import axios, { type AxiosInstance, type InternalAxiosRequestConfig, isAxiosError } from 'axios'

import type { CreateConversationResponse, DeleteSourceResponse, GetConversationResponse, GetSourcesResponse, SourceReportResponse, UploadSourceResponse } from './types'

export type AuthHandlers = {
    refreshToken: () => Promise<string | null>;
    onUnauthorized: () => Promise<void>;
}

type RetriedRequestConfig = InternalAxiosRequestConfig & {
    retriedAfterRefresh?: boolean;
}

class ApiService {
    private apiHost = import.meta.env.BACKEND_URL
    private token: string | null = null
    private client: AxiosInstance
    private authHandlers: AuthHandlers | null = null
    private refreshInFlight: Promise<string | null> | null = null

    constructor() {
        this.client = this.constructClient(this.token)
    }

    private constructClient = (token: string | null) => {
        const client = axios.create({
            baseURL: this.apiHost,
            headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        })

        client.interceptors.response.use((res) => res, this.errorResponseInterceptor)

        return client
    }

    private errorResponseInterceptor = async (error: unknown) => {
        if (!isAxiosError(error) || error.response?.status !== 401 || !error.config) {
            throw error
        }

        const request = error.config as RetriedRequestConfig
        if (!request.retriedAfterRefresh) {
            request.retriedAfterRefresh = true
            const token = await this.refreshToken()

            if (token) {
                request.headers.Authorization = `Bearer ${token}`
                return this.client.request(request)
            }
        }

        await this.authHandlers?.onUnauthorized()
        throw error
    }

    private refreshToken = (): Promise<string | null> => {
    // Parallel requests failing at once must not trigger parallel refreshes.
        this.refreshInFlight ??= this.requestRefreshedToken()
        return this.refreshInFlight
    }

    private requestRefreshedToken = async (): Promise<string | null> => {
        try {
            const token = (await this.authHandlers?.refreshToken()) ?? null
            if (token) {
                this.setToken(token)
            }
            return token
        }
        catch {
            return null
        }
        finally {
            this.refreshInFlight = null
        }
    }

    setAuthHandlers = (handlers: AuthHandlers | null) => {
        this.authHandlers = handlers
    }

    setToken = (token: string | null) => {
        this.token = token
        this.client = this.constructClient(token)
    }

    getConversations = async (): Promise<GetConversationResponse> => {
        const { data } = await this.client.get<GetConversationResponse>('/conversations')
        return data
    }

    createConversation = async (): Promise<CreateConversationResponse> => {
        const { data } = await this.client.post<CreateConversationResponse>('/conversations')
        return data
    }

    getSources = async (conversationId: string): Promise<GetSourcesResponse> => {
        const { data } = await this.client.get<GetSourcesResponse>(`/conversations/${conversationId}/sources`)
        return data
    }

    deleteSource = async (conversationId: string, documentId: string): Promise<DeleteSourceResponse> => {
        const { data } = await this.client.delete<DeleteSourceResponse>(`/conversations/${conversationId}/sources/${documentId}`)
        return data
    }

    editSourceName = async (conversationId: string, documentId: string, name: string): Promise<string> => {
        const { data } = await this.client.patch<string>(`/conversations/${conversationId}/sources/${documentId}`, name)

        return data
    }

    getSourceReport = async (conversationId: string, documentId: string): Promise<SourceReportResponse> => {
        const { data } = await this.client.get<SourceReportResponse>(`/conversations/${conversationId}/sources/${documentId}/report`)
        return data
    }

    uploadSource = async (conversationId: string, formData: FormData): Promise<UploadSourceResponse> => {
        const { data } = await this.client.post<UploadSourceResponse>(`/upload?conversation_id=${encodeURIComponent(conversationId)}`, formData)
        return data
    }
}

export const apiService = new ApiService()
