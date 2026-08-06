/**
 * Crop recovery tracker domain types — mirrors the backend `RecoveryTrackerOut`
 * / `RecoveryLogOut` / `RecoveryLogIn` shapes for the nested
 * `/scans/{id}/recovery` endpoints (see `backend/app/schemas/recovery.py`).
 * The percentage / status / risk are computed server-side policy; the client
 * only renders them.
 */

import type { ScanPartType, ScanSeverity } from "@/types/scan";

/** Farmer-reported crop response for one treatment log. */
export type RecoveryProgress = "worsening" | "no-change" | "improving" | "recovered";

/** Computed recovery band (ascending). */
export type RecoveryStatus = "at_risk" | "on_track" | "improving" | "recovered";

/** Computed risk level for the plant overview. */
export type RiskLevel = "low" | "medium" | "high";

/** Compact scan summary that drives the dashboard's Plant Overview. */
export interface RecoveryScan {
  id: number;
  disease_name: string;
  crop_id: number | null;
  crop_name: string | null;
  part_type: ScanPartType | null;
  severity: ScanSeverity | null;
  stage: string | null;
  confidence: number;
  provider: string;
  model_version: string | null;
  created_at: string;
}

/** One treatment log as returned by the API. */
export interface RecoveryLog {
  id: number;
  scan_id: number;
  treatment_applied: string;
  notes: string | null;
  progress: RecoveryProgress | null;
  applied_at: string;
  created_at: string;
}

/** Payload for POST /scans/{id}/recovery/logs (applied_at defaults to now). */
export interface RecoveryLogInput {
  treatment_applied: string;
  notes?: string | null;
  progress?: RecoveryProgress | null;
  applied_at?: string | null;
}

/** Full recovery section for one scan. */
export interface RecoveryTracker {
  scan: RecoveryScan;
  risk: RiskLevel;
  /** Estimated recovery progress (0–1). */
  recovery_percentage: number;
  status: RecoveryStatus;
  total_treatments: number;
  timeline: RecoveryLog[];
  updated_at: string | null;
}
