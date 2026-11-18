import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, CalendarPlus, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

/**
 * "Schedule a crop" card: pick any catalog crop with a growth-stage template
 * and start its calendar. The planting date defaults to today (or the next
 * sowing window) server-side; the farmer can override it with the optional
 * date field. On success the parent refetches the dashboard.
 */
export function CalendarCropPicker({
  onScheduled,
}: {
  onScheduled: () => void;
}) {
  const { t } = useTranslation();
  const [cropId, setCropId] = useState("");
  const [plantingDate, setPlantingDate] = useState("");

  const cropsQuery = useQuery({
    queryKey: ["calendar-crops"],
    queryFn: () => api.listCalendarCrops(),
    retry: false,
  });

  const scheduleMutation = useMutation({
    mutationFn: (id: number) =>
      api.scheduleCrop(id, plantingDate ? { planting_date: plantingDate } : {}),
    onSuccess: () => {
      setPlantingDate("");
      onScheduled();
    },
  });

  const submit = () => {
    const id = Number(cropId);
    if (!Number.isInteger(id) || scheduleMutation.isPending) return;
    scheduleMutation.mutate(id);
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarPlus className="size-4 text-brand-600 dark:text-brand-400" aria-hidden="true" />
          {t("calendar.picker.title")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {cropsQuery.isPending ? (
          <div role="status" aria-label={t("calendar.picker.loading")} className="flex flex-col gap-2">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : cropsQuery.isError ? (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="size-4" aria-hidden="true" />
            {t("calendar.picker.error")}
          </div>
        ) : cropsQuery.data && cropsQuery.data.length > 0 ? (
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <div className="flex flex-1 flex-col gap-2">
              <Label htmlFor="calendar-crop">{t("calendar.picker.cropLabel")}</Label>
              <Select
                id="calendar-crop"
                value={cropId}
                onChange={(event) => setCropId(event.target.value)}
              >
                <option value="">{t("calendar.picker.cropPlaceholder")}</option>
                {cropsQuery.data.map((crop) => (
                  <option key={crop.id} value={crop.id}>
                    {crop.common_name ?? crop.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex flex-col gap-2 sm:w-44">
              <Label htmlFor="calendar-planting">{t("calendar.picker.dateLabel")}</Label>
              <input
                id="calendar-planting"
                type="date"
                value={plantingDate}
                onChange={(event) => setPlantingDate(event.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>
            <Button
              onClick={submit}
              disabled={!cropId || scheduleMutation.isPending}
              className="sm:w-auto"
            >
              {scheduleMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <CalendarPlus className="size-4" aria-hidden="true" />
              )}
              {t("calendar.picker.schedule")}
            </Button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t("calendar.picker.empty")}</p>
        )}
        {scheduleMutation.isError && (
          <p role="alert" className="mt-3 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="size-4" aria-hidden="true" />
            {t("calendar.picker.errorSchedule")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
