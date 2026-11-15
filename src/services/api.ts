/** Typed client for the optional local TERRASCAN API. No scientific data is seeded. */
let apiAccessToken: string | null = null;
export function setApiAccessToken(token: string | null) { apiAccessToken = token; }

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export interface ApiHealth { status: 'ok'; service: string; version: string; database: string }
export interface ApiCollection<T> { items: T[]; limit?: number; offset?: number }
export interface DatasetManifest {
  id: string; dataset_id: string; version: string; sha256: string; source_uri: string;
  review_status: 'pending-human-review' | 'approved' | 'rejected'; metadata: Record<string, unknown>; created_at: string;
}
export interface ScientificObservation {
  id: string; site_id: string; target_body: 'Earth' | 'Moon' | 'Mars'; criterion: string;
  value: number; unit: string; manifest_id: string; quality: string; metadata: Record<string, unknown>; created_at: string; review_status?: 'pending-human-review' | 'approved' | 'rejected'; reviewed_at?: string | null; reviewer?: string | null; review_reason?: string | null;
}
export interface TargetProfile {
  id: string; target_body: 'Moon' | 'Mars'; feature_key: string; value: number;
  unit: string; metadata: Record<string, unknown>; created_at: string;
}
export interface ScientificReportSummary {
  schema_version: string; generated_at: string; target_body: 'Moon' | 'Mars';
  observations: Array<Record<string, unknown>>;
  target_references: Array<Record<string, unknown>>;
  approved_manifests: Array<Record<string, unknown>>;
  review_queue: { pending_manifests: number; pending_observations: number; rejected_observations: number };
  comparison_status: 'not-computed'; interpretation: string;
}
export interface ComparisonRun {
  id: string; target_body: 'Moon' | 'Mars'; status: 'queued' | 'completed' | 'failed';
  input_snapshot: Record<string, unknown>; result: Record<string, unknown> | null; created_at: string; completed_at: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(apiAccessToken ? { Authorization: `Bearer ${apiAccessToken}` } : {}), ...init?.headers },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail || `TERRASCAN API error (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const terrascanApi = {
  health: () => request<ApiHealth>('/api/health'),
  manifests: () => request<ApiCollection<DatasetManifest>>('/api/manifests'),
  observations: () => request<ApiCollection<ScientificObservation>>('/api/observations'),
  targetProfiles: (body?: 'Moon' | 'Mars') => request<ApiCollection<TargetProfile>>(`/api/target-profiles${body ? `?target_body=${body}` : ''}`),
  reviewQueue: () => request<{ manifests: DatasetManifest[]; observations: ScientificObservation[]; counts: { manifests: number; observations: number } }>('/api/review-queue'),
  reviewManifest: (id: string, decision: 'approved' | 'rejected', reason: string, reviewer: string) =>
    request<DatasetManifest>(`/api/manifests/${encodeURIComponent(id)}/review`, { method: 'POST', body: JSON.stringify({ decision, reason, reviewer }) }),
  reviewObservation: (id: string, decision: 'approved' | 'rejected', reason: string, reviewer: string) =>
    request<ScientificObservation>(`/api/observations/${encodeURIComponent(id)}/review`, { method: 'POST', body: JSON.stringify({ decision, reason, reviewer }) }),
  reportSummary: (body: 'Moon' | 'Mars') => request<ScientificReportSummary>(`/api/reports/${body}/summary`),
  reviewHistory: () => request<ApiCollection<Record<string, unknown>>>('/api/review-history'),
  comparisonRuns: () => request<ApiCollection<ComparisonRun>>('/api/comparison-runs'),
};
