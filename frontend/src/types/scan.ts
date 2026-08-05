/**
 * Scan domain types — mirrors the backend `ScanOut` / `ScanListOut` response
 * shapes plus the query parameters of `GET /scans` (see
 * `backend/app/schemas/scan.py` and `endpoints/scans.py::list_my_scans`).
 */

export interface ScanMediaItem {
  source_type: "upload" | "sync";
  path: string;
  url: string;
  part_type: string | null;
  width: number;
  height: number;
  content_type: string;
}

export interface ScanRanking {
  disease_name: string;
  confidence: number;
  disease_id: number | null;
  crop_id: number | null;
}

export type ScanPartType = "leaf" | "fruit" | "stem" | "plant" | "whole";
export type ScanSeverity = "low" | "moderate" | "severe";
export type ScanSyncStatus = "synced" | "pending" | "failed";

export interface Scan {
  id: number;
  client_scan_id: string;
  crop_id: number | null;
  part_type: ScanPartType | null;
  disease_id: number | null;
  disease_name: string;
  confidence: number;
  severity: ScanSeverity | null;
  stage: string | null;
  provider: string;
  model_name: string | null;
  model_version: string | null;
  dataset_version: string | null;
  preprocessing_time_ms: number;
  inference_time_ms: number;
  processing_time_ms: number;
  image_path: string;
  processed_image_path: string | null;
  heatmap_path: string | null;
  media_items: ScanMediaItem[];
  sync_status: ScanSyncStatus;
  synced_at: string | null;
  rankings: ScanRanking[];
  ai_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ScanList {
  items: Scan[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export type ScanSort = "created_at" | "confidence" | "disease_name";
export type ScanOrder = "asc" | "desc";

export interface ScanListParams {
  page?: number;
  page_size?: number;
  sort?: ScanSort;
  order?: ScanOrder;
  search?: string;
  crop_id?: number;
  disease?: string;
  part_type?: ScanPartType;
  date_from?: string;
  date_to?: string;
  confidence_min?: number;
  confidence_max?: number;
  severity?: ScanSeverity;
  sync_status?: ScanSyncStatus;
}

/** One catalog crop — the crop-filter dropdown option. */
export interface CropOption {
  id: number;
  name: string;
  common_name: string | null;
}

// ── Explainability (GET /scans/{id}/explain) ─────────────────────────────

export type ConfidenceLevel = "high" | "medium" | "low";

export interface ExplainDisease {
  id: number | null;
  name: string;
  crop_id: number | null;
  severity: ScanSeverity | null;
  stage: string | null;
  symptoms: string[];
}

export interface ExplainConfidence {
  top: number;
  level: ConfidenceLevel;
  advice: string;
}

export interface ExplainHeatmap {
  provider: string;
  class_name: string;
  time_ms: number;
}

export interface ExplainTiming {
  preprocessing_time_ms: number;
  inference_time_ms: number;
  processing_time_ms: number;
  heatmap_time_ms: number | null;
}

export interface ExplainModel {
  provider: string;
  model_name: string | null;
  model_version: string | null;
  dataset_version: string | null;
}

export interface ScanExplain {
  scan_id: number;
  disease: ExplainDisease;
  confidence: ExplainConfidence;
  top5: ScanRanking[];
  heatmap: ExplainHeatmap | null;
  heatmap_url: string | null;
  overlay_url: string | null;
  explanation: string;
  timing: ExplainTiming;
  model: ExplainModel;
}
