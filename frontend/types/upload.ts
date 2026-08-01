/**
 * Odwzorowanie odpowiedzi backendu POST /upload.
 * Nazwy pól celowo zostają w snake_case — to surowy kształt JSON-a z FastAPI.
 */

/** Pozycja z audytu markdownu: audit_markdown() w quality_audit.py */
export type ParseIssue = {
  line: number
  kinds: string[]
  text: string
}

export type ParseReport = {
  ok: boolean
  /** Liczba wystąpień per rodzaj defektu, np. { unresolved_glyph: 3 } */
  counts: Record<string, number>
  issues: ParseIssue[]
}

export type RejectedChunk = {
  index: number
  kinds: string[]
  text: string
}

export type ChunkQuality = {
  ok: boolean
  total_chunks: number
  kept_chunks: number
  rejected_chunks: number
  rejected_ratio: number
  max_rejected_ratio: number
  rejected: RejectedChunk[]
}

export type UploadQuality = {
  parse_report: ParseReport
  chunk_quality: ChunkQuality
}

/** 200 — dokument sparsowany, pochunkowany i zaindeksowany. */
export type UploadOkResponse = {
  status: "ok"
  conversation_id: string
  document_id: string
  parsed_content: string
  quality: UploadQuality
}

/**
 * 422 — ParseQualityError. Raport ma inny kształt niż przy 200:
 * pola parse_report są rozpłaszczone na wierzchu, a chunk_quality
 * dodatkowo zawiera kept_indexes.
 */
export type UploadRejectedResponse = {
  status: "rejected"
  document_id: string | null
  detail: string
  report: ParseReport & {
    chunk_quality: ChunkQuality & { kept_indexes: number[] }
  }
}

/** 404 i pozostałe HTTPException z FastAPI. */
export type ApiErrorResponse = {
  detail: string
}

export type UploadResponse = UploadOkResponse | UploadRejectedResponse

export function isUploadOk(response: UploadResponse): response is UploadOkResponse {
  return response.status === "ok"
}
