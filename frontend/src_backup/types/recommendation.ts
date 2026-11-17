/**
 * Treatment recommendation domain types — mirrors the backend
 * `DiseaseRecommendationOut` response shape for `GET /scans/{id}/recommendations`
 * (see `backend/app/schemas/recommendation.py`). Self-contained: the client
 * needs no other call to render a care plan. Lists are always present
 * (never null) so the UI can map over them safely; scalar guidance fields
 * (`watering`, `temperature`, …) may be null when a plan wasn't curated yet.
 */

export interface HomemadeRemedy {
  title: string;
  category: string;
  ingredients: string[];
  instructions: string;
  frequency: string;
}

export interface OrganicRemedy {
  title: string;
  category: string;
  application: string;
  frequency: string;
}

export interface ChemicalRecommendation {
  category: string;
  product: string;
  dosage: string;
  application_interval: string;
  safety_precautions: string[];
}

export interface RecommendationDisease {
  id: number;
  name: string;
  crop_id: number | null;
  crop_name: string | null;
}

export interface DiseaseRecommendation {
  catalog_version: string;
  disease: RecommendationDisease;
  overview: string | null;
  cause: string | null;
  symptoms: string[];
  severity: string | null;
  spread_mechanism: string | null;
  homemade_remedies: HomemadeRemedy[];
  organic_remedies: OrganicRemedy[];
  chemical_recommendations: ChemicalRecommendation[];
  fertilizer: string | null;
  watering: string | null;
  sunlight: string | null;
  temperature: string | null;
  humidity: string | null;
  prevention_tips: string[];
  recovery_timeline: string | null;
  isolation: string | null;
  monitoring_advice: string[];
}
