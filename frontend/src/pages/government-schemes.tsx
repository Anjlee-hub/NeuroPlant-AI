import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Landmark,
  Search,
  ShieldCheck,
  ShieldQuestion,
  XCircle,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { EligibilityCheckInput, GovernmentScheme } from "@/types/scheme";

const PAGE_SIZE = 20;

export function GovernmentSchemesPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [stateCode, setStateCode] = useState("");
  const [cropName, setCropName] = useState("");
  const [farmerCategory, setFarmerCategory] = useState("");
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedSchemeId, setSelectedSchemeId] = useState<number | null>(null);
  const [eligibilityState, setEligibilityState] = useState("");
  const [eligibilityCrop, setEligibilityCrop] = useState("");
  const [eligibilityCategory, setEligibilityCategory] = useState("");

  const schemesQuery = useQuery({
    queryKey: [
      "government-schemes",
      stateCode,
      cropName,
      farmerCategory,
      category,
      page,
    ],
    queryFn: () =>
      api.listGovernmentSchemes({
        state_code: stateCode.trim() || undefined,
        crop_name: cropName.trim() || undefined,
        farmer_category: farmerCategory.trim() || undefined,
        category: category.trim() || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: !!user,
  });

  const selectedSchemeQuery = useQuery({
    queryKey: ["government-scheme", selectedSchemeId],
    queryFn: () => api.getGovernmentScheme(selectedSchemeId!),
    enabled: !!user && selectedSchemeId !== null,
  });

  const eligibilityMutation = useMutation({
    mutationFn: ({
      schemeId,
      payload,
    }: {
      schemeId: number;
      payload: EligibilityCheckInput;
    }) => api.checkSchemeEligibility(schemeId, payload),
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard
          icon={Landmark}
          title={t("schemes.authTitle")}
          body={t("schemes.authBody")}
        >
          <Button asChild>
            <Link to="/login">{t("schemes.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const items = schemesQuery.data?.items ?? [];
  const visibleItems = items.filter((scheme) => {
    const term = search.trim().toLocaleLowerCase();
    return (
      !term ||
      [scheme.name, scheme.description, scheme.category, scheme.source_name]
        .join(" ")
        .toLocaleLowerCase()
        .includes(term)
    );
  });

  function updateFilter(setter: (value: string) => void, value: string) {
    setter(value);
    setPage(1);
  }

  function openScheme(scheme: GovernmentScheme) {
    setSelectedSchemeId(scheme.id);
    setEligibilityState(stateCode);
    setEligibilityCrop(cropName);
    setEligibilityCategory(farmerCategory);
    eligibilityMutation.reset();
  }

  function checkEligibility(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedSchemeId === null) return;

    const payload: EligibilityCheckInput = {};
    if (eligibilityState.trim()) payload.state_code = eligibilityState.trim();
    if (eligibilityCrop.trim()) payload.crop_name = eligibilityCrop.trim();
    if (eligibilityCategory.trim()) {
      payload.farmer_category = eligibilityCategory.trim();
    }

    eligibilityMutation.reset();
    eligibilityMutation.mutate({ schemeId: selectedSchemeId, payload });
  }

  const selectedScheme = selectedSchemeQuery.data;
  const eligibility = eligibilityMutation.data;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
          <Landmark className="size-7 text-brand-600 dark:text-brand-400" />
          {t("schemes.title")}
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          {t("schemes.subtitle")}
        </p>
      </header>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">{t("schemes.filtersTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <FilterField
            id="scheme-state-filter"
            label={t("schemes.state")}
            placeholder={t("schemes.statePlaceholder")}
            value={stateCode}
            onChange={(value) => updateFilter(setStateCode, value)}
          />
          <FilterField
            id="scheme-crop-filter"
            label={t("schemes.crop")}
            placeholder={t("schemes.cropPlaceholder")}
            value={cropName}
            onChange={(value) => updateFilter(setCropName, value)}
          />
          <FilterField
            id="scheme-farmer-category-filter"
            label={t("schemes.farmerCategory")}
            placeholder={t("schemes.categoryPlaceholder")}
            value={farmerCategory}
            onChange={(value) => updateFilter(setFarmerCategory, value)}
          />
          <div className="space-y-2">
            <Label htmlFor="scheme-category-filter">{t("schemes.schemeCategory")}</Label>
            <Input
              id="scheme-category-filter"
              value={category}
              placeholder={t("schemes.schemeCategoryPlaceholder")}
              onChange={(event) => updateFilter(setCategory, event.target.value)}
            />
          </div>
          <div className="space-y-2 sm:col-span-2 lg:col-span-4">
            <Label htmlFor="scheme-search">{t("schemes.searchPageLabel")}</Label>
            <div className="relative">
              <Search
                aria-hidden="true"
                className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                id="scheme-search"
                className="pl-9"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("schemes.searchPlaceholder")}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {schemesQuery.isPending ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2" role="status" aria-label={t("schemes.loading")}>
          <Skeleton className="h-52 w-full" />
          <Skeleton className="h-52 w-full" />
        </div>
      ) : schemesQuery.isError ? (
        <StateCard
          className="mt-6"
          icon={AlertCircle}
          tone="destructive"
          title={t("schemes.errorTitle")}
          body={errorMessage(schemesQuery.error)}
        >
          <Button variant="outline" onClick={() => void schemesQuery.refetch()}>
            {t("common.retry")}
          </Button>
        </StateCard>
      ) : schemesQuery.data?.source_status === "no_scheme_records" ? (
        <StateCard
          className="mt-6"
          icon={Landmark}
          title={t("schemes.emptyTitle")}
          body={schemesQuery.data.source_note}
        />
      ) : (
        <div>
          <p className="mt-5 text-sm text-muted-foreground" aria-live="polite">
            {t("schemes.resultCount", { count: schemesQuery.data?.total ?? 0 })}
          </p>
          {visibleItems.length === 0 ? (
            <StateCard
              className="mt-3"
              icon={Search}
              title={t("schemes.noMatchesTitle")}
              body={t("schemes.noMatchesBody")}
            />
          ) : (
            <section aria-label={t("schemes.listLabel")} className="mt-3 grid gap-4 md:grid-cols-2">
              {visibleItems.map((scheme) => (
                <SchemeCard
                  key={scheme.id}
                  scheme={scheme}
                  selected={scheme.id === selectedSchemeId}
                  onSelect={() => openScheme(scheme)}
                  t={t}
                />
              ))}
            </section>
          )}
          {(schemesQuery.data?.pages ?? 0) > 1 && (
            <nav className="mt-6 flex items-center justify-center gap-3" aria-label={t("schemes.pagination")}>
              <Button
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                {t("schemes.previous")}
              </Button>
              <span className="text-sm text-muted-foreground">
                {t("schemes.pageOf", {
                  page,
                  pages: schemesQuery.data?.pages ?? 1,
                })}
              </span>
              <Button
                variant="outline"
                disabled={page >= (schemesQuery.data?.pages ?? 1)}
                onClick={() => setPage((current) => current + 1)}
              >
                {t("schemes.next")}
              </Button>
            </nav>
          )}
        </div>
      )}

      {selectedSchemeId !== null && (
        <section className="mt-8" aria-label={t("schemes.detailsLabel")}>
          {selectedSchemeQuery.isPending ? (
            <Card role="status">
              <CardContent className="space-y-3 p-6">
                <Skeleton className="h-7 w-1/2" />
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ) : selectedSchemeQuery.isError ? (
            <StateCard
              icon={AlertCircle}
              tone="destructive"
              title={t("schemes.detailsErrorTitle")}
              body={errorMessage(selectedSchemeQuery.error)}
            >
              <Button variant="outline" onClick={() => void selectedSchemeQuery.refetch()}>
                {t("common.retry")}
              </Button>
            </StateCard>
          ) : selectedScheme ? (
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-xl">{selectedScheme.name}</CardTitle>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {selectedScheme.category}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedSchemeId(null);
                      eligibilityMutation.reset();
                    }}
                  >
                    {t("schemes.closeDetails")}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <p className="whitespace-pre-line text-sm">{selectedScheme.description}</p>
                {selectedScheme.benefits && (
                  <InfoBlock title={t("schemes.benefits")} text={selectedScheme.benefits} />
                )}
                {selectedScheme.subsidy_details && (
                  <InfoBlock title={t("schemes.subsidyDetails")} text={selectedScheme.subsidy_details} />
                )}
                {selectedScheme.eligibility_requirements.length > 0 && (
                  <ListBlock
                    title={t("schemes.requirements")}
                    items={selectedScheme.eligibility_requirements}
                  />
                )}
                {selectedScheme.required_documents.length > 0 && (
                  <ListBlock
                    title={t("schemes.documents")}
                    items={selectedScheme.required_documents}
                  />
                )}
                {selectedScheme.application_instructions && (
                  <InfoBlock
                    title={t("schemes.instructions")}
                    text={selectedScheme.application_instructions}
                  />
                )}
                <div className="flex flex-wrap gap-2 text-sm">
                  {selectedScheme.state_codes.map((item) => (
                    <Badge key={item} variant="secondary">{item}</Badge>
                  ))}
                  {selectedScheme.crops.map((item) => (
                    <Badge key={item} variant="outline">{item}</Badge>
                  ))}
                  {selectedScheme.farmer_categories.map((item) => (
                    <Badge key={item} variant="outline">{item}</Badge>
                  ))}
                </div>
                <div className="rounded-lg border bg-muted/30 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <ShieldCheck className="size-4 text-muted-foreground" />
                    <span className="font-medium">{t("schemes.sourceAttribution")}</span>
                    <Badge variant={selectedScheme.is_verified ? "success" : "outline"}>
                      {selectedScheme.is_verified
                        ? t("schemes.verified")
                        : t("schemes.unverified")}
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm">{selectedScheme.source_name}</p>
                  <a
                    className="mt-1 inline-flex items-center gap-1 break-all text-sm text-primary underline"
                    href={selectedScheme.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {selectedScheme.source_url}
                    <ExternalLink aria-hidden="true" className="size-3 shrink-0" />
                  </a>
                  {selectedScheme.last_verified_at && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      {t("schemes.lastVerified", {
                        date: new Date(selectedScheme.last_verified_at).toLocaleDateString(),
                      })}
                    </p>
                  )}
                  {selectedScheme.official_application_url && (
                    <a
                      className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary underline"
                      href={selectedScheme.official_application_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {t("schemes.officialApplication")}
                      <ExternalLink aria-hidden="true" className="size-3" />
                    </a>
                  )}
                </div>

                <div className="border-t pt-5">
                  <h3 className="text-lg font-semibold">{t("schemes.eligibilityTitle")}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("schemes.eligibilityDisclaimer")}
                  </p>
                  <form
                    className="mt-4 grid gap-4 sm:grid-cols-3"
                    onSubmit={checkEligibility}
                  >
                    <FilterField
                      id="eligibility-state"
                      label={t("schemes.state")}
                      placeholder={t("schemes.statePlaceholder")}
                      value={eligibilityState}
                      onChange={setEligibilityState}
                    />
                    <FilterField
                      id="eligibility-crop"
                      label={t("schemes.crop")}
                      placeholder={t("schemes.cropPlaceholder")}
                      value={eligibilityCrop}
                      onChange={setEligibilityCrop}
                    />
                    <FilterField
                      id="eligibility-farmer-category"
                      label={t("schemes.farmerCategory")}
                      placeholder={t("schemes.categoryPlaceholder")}
                      value={eligibilityCategory}
                      onChange={setEligibilityCategory}
                    />
                    <div className="sm:col-span-3">
                      <Button type="submit" disabled={eligibilityMutation.isPending}>
                        {eligibilityMutation.isPending
                          ? t("schemes.checking")
                          : t("schemes.checkEligibility")}
                      </Button>
                    </div>
                  </form>

                  {eligibilityMutation.isError && (
                    <div className="mt-4 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm">
                      <p className="font-medium">{t("schemes.eligibilityErrorTitle")}</p>
                      <p className="mt-1">{errorMessage(eligibilityMutation.error)}</p>
                    </div>
                  )}
                  {eligibility && (
                    <EligibilityResult result={eligibility} t={t} />
                  )}
                </div>
              </CardContent>
            </Card>
          ) : null}
        </section>
      )}
    </main>
  );
}

function FilterField({
  id,
  label,
  placeholder,
  value,
  onChange,
}: {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function SchemeCard({
  scheme,
  selected,
  onSelect,
  t,
}: {
  scheme: GovernmentScheme;
  selected: boolean;
  onSelect: () => void;
  t: (key: string, options?: Record<string, unknown>) => string;
}) {
  return (
    <Card className={selected ? "border-primary" : ""}>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">{scheme.name}</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">{scheme.category}</p>
          </div>
          <Badge variant={scheme.is_verified ? "success" : "outline"}>
            {scheme.is_verified ? t("schemes.verified") : t("schemes.unverified")}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="line-clamp-3 text-sm text-muted-foreground">{scheme.description}</p>
        <p className="mt-4 text-xs text-muted-foreground">
          {t("schemes.source")}: {scheme.source_name}
        </p>
        <Button className="mt-4" variant="outline" onClick={onSelect}>
          {t("schemes.detailsAndEligibility")}
        </Button>
      </CardContent>
    </Card>
  );
}

function InfoBlock({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-1 whitespace-pre-line text-sm text-muted-foreground">{text}</p>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-muted-foreground">
        {items.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}
      </ul>
    </div>
  );
}

function EligibilityResult({
  result,
  t,
}: {
  result: {
    outcome: "potentially_eligible" | "not_eligible" | "unknown";
    matched_rules: string[];
    unmet_rules: string[];
    explanation: string;
    legal_determination: false;
  };
  t: (key: string) => string;
}) {
  const states = {
    potentially_eligible: {
      label: t("schemes.potentiallyEligible"),
      icon: CheckCircle2,
      style: "border-brand-300 bg-brand-50 dark:border-brand-800 dark:bg-brand-950/40",
    },
    not_eligible: {
      label: t("schemes.notEligible"),
      icon: XCircle,
      style: "border-destructive/40 bg-destructive/5",
    },
    unknown: {
      label: t("schemes.unknownEligibility"),
      icon: ShieldQuestion,
      style: "border-border bg-muted/40",
    },
  } as const;
  const state = states[result.outcome];
  const Icon = state.icon;

  return (
    <div className={`mt-4 rounded-lg border p-4 ${state.style}`} aria-live="polite">
      <div className="flex items-center gap-2 font-semibold">
        <Icon className="size-5" />
        {state.label}
      </div>
      <p className="mt-2 text-sm">{result.explanation}</p>
      {result.matched_rules.length > 0 && (
        <ListBlock title={t("schemes.matchedRules")} items={result.matched_rules} />
      )}
      {result.unmet_rules.length > 0 && (
        <div className="mt-3">
          <ListBlock title={t("schemes.unmetOrUnknownRules")} items={result.unmet_rules} />
        </div>
      )}
      <p className="mt-3 text-xs text-muted-foreground">
        {t("schemes.notLegalDetermination")}
      </p>
    </div>
  );
}
