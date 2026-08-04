import type { ResourceReport } from '@/types/report'
import type { Resource } from '@/types/resource'

export type ResourceResponse = Resource

export type GetResourcesResponse = {
    count: number;
    conversationResources: ResourceResponse[];
}

export type ResourceReportResponse = ResourceReport

export type UploadResourceResponse = {
    resource: ResourceResponse | null;
    report: ResourceReportResponse | null;
    error: string | null;
}
