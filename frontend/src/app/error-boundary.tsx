import { AlertTriangle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { isRouteErrorResponse, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";

/**
 * Router-level error boundary. Catches render errors thrown by any matched
 * route. 404s inside the layout are handled by the catch-all route instead;
 * this boundary is for unexpected failures (500).
 */
export function ErrorBoundary() {
  const error = useRouteError();
  const { t } = useTranslation();

  const status = isRouteErrorResponse(error) ? error.status : 500;
  const title = isRouteErrorResponse(error) ? error.statusText : t("common.error");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <AlertTriangle className="size-10 text-destructive" />
      <div>
        <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
          {status}
        </p>
        <h1 className="mt-2 text-2xl font-bold">{title}</h1>
        <p className="mt-2 text-muted-foreground">{t("common.pageErrorBody")}</p>
      </div>
      <Button onClick={() => window.location.assign("/")}>
        {t("common.backHome")}
      </Button>
    </main>
  );
}
