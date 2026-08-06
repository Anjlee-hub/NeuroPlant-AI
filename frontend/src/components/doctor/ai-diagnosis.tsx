import { Eye, Wand2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatMs, formatPercent } from "@/lib/format";
import type { ScanExplain } from "@/types/scan";

/**
 * AI Diagnosis — the explainability section of the Crop Doctor dashboard: the
 * plain-language explanation, the symptoms the model keyed on ("what the AI
 * observed"), the Grad-CAM heatmap overlay, and the ranked top-5 predictions.
 * Reads only the already-persisted explain payload (no re-inference).
 */
export function AiDiagnosis({ explain }: { explain: ScanExplain | null }) {
  const { t } = useTranslation();

  if (!explain) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("doctor.diagnosis")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-2 p-6 text-center">
          <Wand2 className="size-8 text-muted-foreground" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">{t("scanDetail.noHeatmapBody")}</p>
        </CardContent>
      </Card>
    );
  }

  const symptoms = explain.disease.symptoms ?? [];

  return (
    <section className="flex flex-col gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("doctor.explanation")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{explain.explanation}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("doctor.whatAiObserved")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t("doctor.aiObservedIntro")}</p>
          {symptoms.length > 0 ? (
            <ul className="mt-3 flex flex-col gap-2">
              {symptoms.map((symptom, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <Eye
                    className="mt-0.5 size-4 shrink-0 text-brand-600 dark:text-brand-400"
                    aria-hidden="true"
                  />
                  <span>{symptom}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">{t("doctor.noSymptoms")}</p>
          )}
        </CardContent>
      </Card>

      {explain.overlay_url && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("doctor.heatmap")}</CardTitle>
          </CardHeader>
          <CardContent>
            <img
              src={explain.overlay_url}
              alt={t("doctor.heatmap")}
              className="w-full rounded-md border"
              onError={(event) => {
                event.currentTarget.style.display = "none";
              }}
            />
            {explain.heatmap && (
              <p className="mt-2 text-xs text-muted-foreground">
                {t("doctor.heatmapCaption", {
                  provider: explain.heatmap.provider,
                  time: formatMs(explain.heatmap.time_ms),
                })}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("doctor.topPredictions")}</CardTitle>
        </CardHeader>
        <CardContent>
          {explain.top5.length > 0 ? (
            <ol className="flex flex-col gap-2.5">
              {explain.top5.slice(0, 5).map((ranking, index) => (
                <li key={`${ranking.disease_name}-${index}`}>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="flex min-w-0 items-center gap-2.5">
                      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                        {index + 1}
                      </span>
                      <span className="truncate font-medium">{ranking.disease_name}</span>
                    </span>
                    <span className="shrink-0 font-semibold">
                      {formatPercent(ranking.confidence)}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-brand-500"
                      style={{ width: `${Math.round(ranking.confidence * 100)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-muted-foreground">{t("doctor.noTop5")}</p>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
