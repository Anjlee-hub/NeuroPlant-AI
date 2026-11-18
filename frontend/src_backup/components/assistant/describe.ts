/**
 * Speakable-text builders for every major recommendation section (M3, Task 6).
 * Each panel renders the same data model; these helpers flatten it into one
 * plain-text string that the SpeakButton reads aloud. Keeping the flattening
 * here (not in the panels) means the read-aloud text and any future voice
 * summary share a single source of truth. Catalog content stays English,
 * exactly like every other UI surface.
 */

import type { CropCalendar } from "@/types/calendar";
import type { DiseaseRecommendation } from "@/types/recommendation";
import type { RecoveryScan, RecoveryTracker, RiskLevel } from "@/types/recovery";
import type { ScanExplain } from "@/types/scan";
import type { SoilRecommendation } from "@/types/soil";

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function dateOf(iso: string): string {
  return iso.slice(0, 10);
}

/** Flatten the full treatment care plan into read-aloud text. */
export function describeRecommendation(rec: DiseaseRecommendation): string {
  const parts: string[] = [];
  const disease = rec.disease.name;
  const crop = rec.disease.crop_name;
  parts.push(crop ? `${disease} on ${crop}.` : `${disease}.`);
  if (rec.overview) parts.push(rec.overview);
  if (rec.cause) parts.push(`Cause: ${rec.cause}`);
  if (rec.spread_mechanism) parts.push(`How it spreads: ${rec.spread_mechanism}`);
  for (const remedy of rec.homemade_remedies) {
    parts.push(`Homemade remedy: ${remedy.title}. ${remedy.instructions} Apply ${remedy.frequency}.`);
  }
  for (const remedy of rec.organic_remedies) {
    parts.push(`Organic remedy: ${remedy.title}. ${remedy.application} Apply ${remedy.frequency}.`);
  }
  for (const chemical of rec.chemical_recommendations) {
    parts.push(
      `Chemical option: ${chemical.product}. Dosage ${chemical.dosage}, apply ${chemical.application_interval}.`,
    );
  }
  for (const [label, value] of [
    ["Fertilizer", rec.fertilizer],
    ["Watering", rec.watering],
    ["Sunlight", rec.sunlight],
    ["Temperature", rec.temperature],
    ["Humidity", rec.humidity],
  ] as const) {
    if (value) parts.push(`${label}: ${value}`);
  }
  for (const tip of rec.prevention_tips) parts.push(`Prevention: ${tip}`);
  if (rec.recovery_timeline) parts.push(`Recovery timeline: ${rec.recovery_timeline}`);
  if (rec.isolation) parts.push(`Isolation: ${rec.isolation}`);
  for (const advice of rec.monitoring_advice) parts.push(`Monitoring: ${advice}`);
  return parts.join(" ");
}

/** Flatten the disease-aware soil plan into read-aloud text. */
export function describeSoil(rec: SoilRecommendation): string {
  const parts: string[] = [];
  const health = rec.soil_health;
  const crop = rec.disease.crop_name;
  parts.push(
    crop
      ? `Soil health for ${rec.disease.name} on ${crop}: ${health.label}, score ${health.score.toFixed(1)} out of 5.`
      : `Soil health for ${rec.disease.name}: ${health.label}, score ${health.score.toFixed(1)} out of 5.`,
  );
  if (health.summary) parts.push(health.summary);
  for (const [label, value] of [
    ["Recommended soil type", rec.recommended_soil_type],
    ["pH range", rec.ph_range],
    ["Moisture", rec.moisture_level],
    ["Drainage", rec.drainage],
    ["Organic matter", rec.organic_matter],
    ["NPK", rec.npk],
    ["Compost", rec.compost],
    ["Mulching", rec.mulching],
  ] as const) {
    if (value) parts.push(`${label}: ${value}`);
  }
  for (const nutrient of rec.micronutrients) parts.push(`Micronutrients: ${nutrient}`);
  if (rec.soil_suitability) parts.push(`Suitability: ${rec.soil_suitability}`);
  for (const suggestion of rec.improvement_suggestions) parts.push(`Improvement: ${suggestion}`);
  if (rec.disease_soil_notes) parts.push(rec.disease_soil_notes);
  return parts.join(" ");
}

/** Flatten the recovery tracker into read-aloud text. */
export function describeRecovery(tracker: RecoveryTracker): string {
  const parts: string[] = [];
  const crop = tracker.scan.crop_name ?? "your crop";
  const percentDone = percent(tracker.recovery_percentage);
  parts.push(
    `${crop} is ${tracker.status}. ${percentDone} recovered, with ${tracker.risk} risk, after ${tracker.total_treatments} treatments.`,
  );
  for (const log of tracker.timeline.slice(-3)) {
    const note = log.notes ? ` Notes: ${log.notes}` : "";
    parts.push(`Applied ${log.treatment_applied} on ${dateOf(log.applied_at)}.${note}`);
  }
  return parts.join(" ");
}

/** Flatten the Crop Doctor Plant Overview into read-aloud text. */
export function describePlantOverview(scan: RecoveryScan, risk: RiskLevel): string {
  const crop = scan.crop_name ?? "your crop";
  const confidence = percent(scan.confidence);
  const severity = scan.severity ?? "unknown";
  return (
    `${crop}, part ${scan.part_type ?? "unknown"}, disease ${scan.disease_name}. ` +
    `Confidence ${confidence}, severity ${severity}, risk ${risk}. ` +
    `Scanned ${dateOf(scan.created_at)}.`
  );
}

/** Flatten the AI diagnosis explanation into read-aloud text. */
export function describeAiDiagnosis(explain: ScanExplain): string {
  const parts: string[] = [];
  if (explain.explanation) parts.push(explain.explanation);
  const symptoms = explain.disease.symptoms ?? [];
  if (symptoms.length > 0) {
    parts.push(`Symptoms the AI observed: ${symptoms.join(", ")}.`);
  }
  return parts.join(" ");
}

/** Flatten a crop schedule's open reminder tasks into read-aloud text. */
export function describeSchedule(schedule: CropCalendar): string {
  const parts: string[] = [`${schedule.crop_name}, planted ${dateOf(schedule.planting_date)}.`];
  const open = schedule.tasks.filter((task) => task.completed_at === null);
  if (open.length === 0) {
    parts.push("No open tasks.");
  } else {
    parts.push(`${open.length} open tasks.`);
    for (const task of open) {
      parts.push(`${task.title}, due ${dateOf(task.due_at)}.`);
    }
  }
  return parts.join(" ");
}
