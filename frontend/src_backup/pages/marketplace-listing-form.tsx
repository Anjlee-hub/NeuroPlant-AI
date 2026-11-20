import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Store } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ListingForm } from "@/components/marketplace/listing-form";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import {
  MARKETPLACE_LISTINGS_KEY,
  MARKETPLACE_STATS_KEY,
} from "@/pages/marketplace-dashboard";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";

/**
 * Create / edit surface for one crop listing (M4 Task 2). The same page
 * serves both modes: no `:id` → blank form; `:id` → fetches the listing and
 * seeds the form. Saving invalidates the dashboard's list + stats and returns
 * to it, so the farmer never sees stale counts after an edit.
 */
export function MarketplaceListingFormPage() {
  const { t } = useTranslation();
  const { listingId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const editing = listingId !== undefined;
  const listingQuery = useQuery({
    queryKey: ["marketplace-listing", listingId],
    queryFn: () => api.getCropListing(Number(listingId)),
    enabled: editing && !!user,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={Store} title={t("marketplace.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("marketplace.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  if (editing && listingQuery.isPending) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <Skeleton className="h-9 w-64" />
        <div className="mt-6">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="mt-4 h-10 w-full" />
          <Skeleton className="mt-4 h-40 w-full" />
          <Skeleton className="mt-4 h-28 w-full" />
        </div>
      </div>
    );
  }

  if (editing && (listingQuery.isError || !listingQuery.data)) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard
          icon={Store}
          title={t("marketplace.errorTitle")}
          body={t("marketplace.errorBody")}
          tone="destructive"
        >
          <Button variant="outline" onClick={() => void listingQuery.refetch()}>
            {t("common.retry")}
          </Button>
        </StateCard>
      </div>
    );
  }

  const backLink = (
    <Link
      to="/marketplace"
      className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="size-4" aria-hidden />
      {t("marketplace.form.back")}
    </Link>
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <header className="mb-6 flex flex-col gap-2">
        {backLink}
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Store className="size-6 text-brand-600 dark:text-brand-400" />
          {t(editing ? "marketplace.form.titleEdit" : "marketplace.form.titleNew")}
        </h1>
      </header>

      <ListingForm
        listing={listingQuery.data ?? undefined}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: MARKETPLACE_LISTINGS_KEY });
          queryClient.invalidateQueries({ queryKey: MARKETPLACE_STATS_KEY });
          navigate("/marketplace");
        }}
        onCancel={() => navigate("/marketplace")}
      />
    </div>
  );
}
