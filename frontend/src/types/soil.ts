/**
 * Soil recommendation domain types — mirrors the backend
 * `SoilRecommendationOut` response shape for `GET /scans/{id}/soil-recommendations`
 * (see `backend/app/schemas/soil.py`). Self-contained: the client needs no
 * other call to render a soil care plan. Lists are always present (never
 * null); scalar guidance fields may be null when a plan wasn't curated yet.
 */
import type { RecommendationDisease } from "@/types/recommendation";

export interface SoilHealth {
  /** poor | fair | good | excellent */
  label: string;
  /** Estimated soil health score (0–5) */
  score: number;
  /** Plain-language reason for the rating */
  summary: string;
}

export interface SoilRecommendation {
  catalog_version: string;
  disease: RecommendationDisease;

  // Nine guidance areas.
  recommended_soil_type: string | null;
  ph_range: string | null;
  moisture_level: string | null;
  drainage: string | null;
  organic_matter: string | null;
  npk: string | null;
  micronutrients: string[];
  compost: string | null;
  mulching: string | null;

  // Soil-health profile.
  soil_health: SoilHealth;
  soil_suitability: string | null;
  improvement_suggestions: string[];

  // Disease-aware context the advice was adapted for.
  disease_soil_notes: string | null;
  severity: string | null;
  severity_notes: string[];
  confidence: number | null;
  confidence_note: string | null;
}
