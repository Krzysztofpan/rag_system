import type { SourceReport } from '@/types/report'
import type { Source } from '@/types/source'

export type SourceResponse = Source

export type GetSourcesResponse = {
    count: number;
    conversationSources: SourceResponse[];
}

export type SourceReportResponse = SourceReport

export type UploadSourceResponse = {
    source: SourceResponse | null;
    report: SourceReportResponse | null;
    error: string | null;
}
