/**
 * Farmer Calendar types — mirrors the backend `CalendarCropOut` /
 * `CropCalendarOut` / `FarmerCalendarOut` / task payloads
 * (see backend/app/schemas/calendar.py). The calendar is the per-crop planning
 * surface: catalog growth-stage templates feed the crop picker, and each
 * scheduled crop carries its stage ranges + mutable task rows.
 */

/** Growth stages rendered by the crop calendar (ascending). */
export type CropStageName =
  | "planting"
  | "germination"
  | "vegetative"
  | "flowering"
  | "fruiting"
  | "harvest";

export type CalendarTaskKind =
  | "watering"
  | "fertilizer"
  | "organic_treatment"
  | "chemical_treatment"
  | "disease_monitoring"
  | "soil_inspection"
  | "custom";

/** Dashboard bucket a task falls into (computed server-side from due_at). */
export type CalendarTaskBucket = "today" | "upcoming" | "overdue" | "completed";

/** A catalog crop with its growth-stage template (crop-picker option). */
export interface CalendarCrop {
  id: number;
  name: string;
  common_name: string | null;
  growth_days: number | null;
  water_needs: string | null;
  fertilizer_needs: string | null;
  planting_start_month: number;
  planting_end_month: number;
  germination_days: number;
  vegetative_days: number;
  flowering_days: number;
  fruiting_days: number;
  harvest_days: number;
  notes: string | null;
}

/** POST /calendar/crops/{id}/schedule payload. */
export interface ScheduleInput {
  planting_date?: string | null;
  regenerate?: boolean;
}

/** One growth stage with its computed date range. */
export interface CropStage {
  stage: CropStageName;
  start_date: string;
  end_date: string;
}

/** One reminder / task. */
export interface CalendarTask {
  id: number;
  schedule_id: number;
  scan_id: number | null;
  kind: CalendarTaskKind;
  title: string;
  due_at: string;
  completed_at: string | null;
  snooze_count: number;
  notes: string | null;
}

/** PATCH /calendar/tasks/{id} — partial task edit. */
export interface CalendarTaskUpdate {
  completed?: boolean;
  snooze_days?: number;
  due_at?: string | null;
  title?: string;
  notes?: string | null;
}

/** POST /calendar/tasks — a farmer-typed note / to-do. */
export interface CustomTaskInput {
  schedule_id: number;
  title: string;
  due_at?: string | null;
  notes?: string | null;
}

/** One scheduled crop: stage ranges + tasks + completion progress. */
export interface CropCalendar {
  schedule_id: number;
  crop_id: number;
  crop_name: string;
  common_name: string | null;
  planting_date: string;
  stages: CropStage[];
  tasks: CalendarTask[];
  completed: number;
  total: number;
  progress: number;
}

/** GET /calendar — the whole Farmer Calendar dashboard. */
export interface FarmerCalendar {
  schedules: CropCalendar[];
  today_count: number;
  upcoming_count: number;
  overdue_count: number;
  completed_count: number;
}
