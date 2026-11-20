import {
  Check,
  History,
  Pencil,
  ScanLine,
  UserRound,
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAuth } from "@/stores/auth";
import { api, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StateCard } from "@/components/ui/state-card";

/** Label/value pair inside a profile card. */
function ProfileRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-right text-sm font-medium">{children}</dd>
    </div>
  );
}

export function ProfilePage() {
  const { t, i18n } = useTranslation();
  const { user, updateUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Total scans = history count (page_size=1 returns `total` without the list).
  const countQuery = useQuery({
    queryKey: ["scans", "count"],
    queryFn: () => api.listScans({ page: 1, page_size: 1 }),
    enabled: !!user,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={UserRound} title={t("profile.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("profile.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const startEdit = () => {
    setNameDraft(user.name);
    setErrorMsg("");
    setSaved(false);
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
    setErrorMsg("");
  };

  const saveEdit = async () => {
    const name = nameDraft.trim();
    if (!name || name === user.name) {
      cancelEdit();
      return;
    }
    setSaving(true);
    setErrorMsg("");
    try {
      const updated = await api.updateProfile({ name });
      updateUser({ name: updated.name });
      setEditing(false);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setErrorMsg(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{t("profile.title")}</h1>
          <p className="mt-1 text-muted-foreground">{t("profile.subtitle")}</p>
        </div>
        {!editing && (
          <Button variant="outline" onClick={startEdit}>
            <Pencil />
            {t("profile.edit")}
          </Button>
        )}
      </header>

      {/* ── Identity card ───────────────────────────────────────────── */}
      <Card className="mt-6">
        <CardContent className="flex flex-col items-center gap-4 p-6 text-center sm:flex-row sm:items-center sm:gap-6 sm:text-left">
          {/* Profile photo placeholder — real uploads land with the M9
              avatar/identity milestone. */}
          <span
            className="flex size-20 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300"
            role="img"
            aria-label={t("profile.photoPlaceholder")}
          >
            <UserRound className="size-10" />
          </span>

          <div className="min-w-0 flex-1">
            {editing ? (
              <div className="flex flex-col items-center gap-2 sm:items-start">
                <div className="flex w-full flex-col gap-1.5 sm:max-w-xs">
                  <Label htmlFor="profile-name" className="sr-only">
                    {t("profile.name")}
                  </Label>
                  <Input
                    id="profile-name"
                    value={nameDraft}
                    onChange={(event) => setNameDraft(event.target.value)}
                    aria-label={t("profile.name")}
                  />
                </div>
                {errorMsg && <p className="text-sm text-destructive">{errorMsg}</p>}
                <div className="flex items-center gap-2">
                  <Button size="sm" disabled={saving || !nameDraft.trim()} onClick={() => void saveEdit()}>
                    {saving ? t("profile.saving") : t("profile.save")}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={cancelEdit}>
                    <X />
                    {t("profile.cancel")}
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <h2 className="truncate text-xl font-bold">{user.name}</h2>
                <p className="text-sm text-muted-foreground">{t(`auth.roles.${user.role}`)}</p>
                {saved && (
                  <p className="mt-1 inline-flex items-center gap-1 text-sm text-brand-600 dark:text-brand-400">
                    <Check className="size-4" />
                    {t("profile.saved")}
                  </p>
                )}
              </>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {/* ── Account details ───────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("profile.detailsTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y divide-border">
              <ProfileRow label={t("profile.name")}>{user.name}</ProfileRow>
              <ProfileRow label={t("profile.phone")}>{user.phone}</ProfileRow>
              <ProfileRow label={t("profile.email")}>
                {user.email ?? <span className="text-muted-foreground">—</span>}
              </ProfileRow>
              <ProfileRow label={t("profile.role")}>{t(`auth.roles.${user.role}`)}</ProfileRow>
              <ProfileRow label={t("profile.memberSince")}>
                {formatDate(user.created_at, i18n.language)}
              </ProfileRow>
            </dl>
          </CardContent>
        </Card>

        {/* ── Activity ──────────────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t("profile.activityTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y divide-border">
              <ProfileRow label={t("profile.totalScansTitle")}>
                {countQuery.isPending
                  ? "…"
                  : t("profile.totalScans", { count: countQuery.data?.total ?? 0 })}
              </ProfileRow>
            </dl>
            <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
              <Button asChild size="sm">
                <Link to="/scans">
                  <History />
                  {t("profile.viewHistory")}
                </Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link to="/detect">
                  <ScanLine />
                  {t("profile.scanNow")}
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
