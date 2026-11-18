
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  Clock3,
  History,
  Leaf,
  Mail,
  Pencil,
  ScanLine,
  ShieldCheck,
  Sprout,
  UserRound,
  X,
} from "lucide-react";
import { motion } from "motion/react";
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

function ProfileRow({
  label,
  children,
  icon: Icon,
}: {
  label: string;
  children: ReactNode;
  icon?: typeof UserRound;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border/60 py-4 last:border-0">
      <div className="flex min-w-0 items-center gap-3">
        {Icon && (
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
            <Icon className="size-4" />
          </span>
        )}
        <dt className="text-sm text-muted-foreground">{label}</dt>
      </div>
      <dd className="min-w-0 text-right text-sm font-semibold">{children}</dd>
    </div>
  );
}

function ProfileStat({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: ReactNode;
  icon: typeof UserRound;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card p-4">
      <span className="flex size-10 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
        <Icon className="size-5" />
      </span>
      <p className="mt-4 text-2xl font-bold tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
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
    setNameDraft(user.name);
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
    } catch (err) {
      setErrorMsg(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const totalScans = countQuery.data?.total ?? 0;

  return (
    <div className="min-h-full bg-background">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:py-10">
        <motion.header
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-8"
        >
          <div className="flex items-center gap-2 text-sm font-medium text-brand-700 dark:text-brand-400">
            <Sprout className="size-4" />
            NeuroPlant AI
          </div>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                {t("profile.title")}
              </h1>
              <p className="mt-2 max-w-xl text-sm text-muted-foreground sm:text-base">
                {t("profile.subtitle")}
              </p>
            </div>

            {!editing && (
              <Button variant="outline" onClick={startEdit}>
                <Pencil className="size-4" />
                {t("profile.edit")}
              </Button>
            )}
          </div>
        </motion.header>

        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.08 }}
          aria-label={t("profile.detailsTitle")}
        >
          <Card className="overflow-hidden border-border/70 shadow-sm">
            <div className="h-2 bg-gradient-to-r from-brand-800 via-brand-500 to-emerald-300" />
            <CardContent className="p-5 sm:p-8">
              <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
                <div className="relative mx-auto sm:mx-0">
                  <span
                    className="flex size-24 items-center justify-center rounded-full border-4 border-background bg-brand-100 text-brand-700 shadow-md dark:bg-brand-900/50 dark:text-brand-300"
                    role="img"
                    aria-label={t("profile.photoPlaceholder")}
                  >
                    <UserRound className="size-12" />
                  </span>
                  <span className="absolute bottom-1 right-1 size-4 rounded-full border-2 border-background bg-emerald-500" />
                </div>

                <div className="min-w-0 flex-1 text-center sm:text-left">
                  {editing ? (
                    <div className="mx-auto max-w-md sm:mx-0">
                      <Label htmlFor="profile-name" className="mb-2 block text-left">
                        {t("profile.name")}
                      </Label>
                      <Input
                        id="profile-name"
                        value={nameDraft}
                        onChange={(event) => setNameDraft(event.target.value)}
                        aria-label={t("profile.name")}
                        maxLength={100}
                      />

                      {errorMsg && (
                        <p role="alert" className="mt-2 text-sm text-destructive">
                          {errorMsg}
                        </p>
                      )}

                      <div className="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
                        <Button
                          size="sm"
                          disabled={saving || !nameDraft.trim()}
                          onClick={() => void saveEdit()}
                        >
                          <Check className="size-4" />
                          {saving ? t("profile.saving") : t("profile.save")}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={saving}
                          onClick={cancelEdit}
                        >
                          <X className="size-4" />
                          {t("profile.cancel")}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <h2 className="truncate text-2xl font-bold tracking-tight">
                        {user.name}
                      </h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {t(`auth.roles.${user.role}`)}
                      </p>

                      {saved && (
                        <p
                          role="status"
                          className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                        >
                          <Check className="size-3.5" />
                          {t("profile.saved")}
                        </p>
                      )}
                    </>
                  )}
                </div>

                <div className="hidden shrink-0 rounded-2xl bg-brand-50 p-4 text-brand-800 dark:bg-brand-950/40 dark:text-brand-200 sm:block">
                  <ShieldCheck className="size-9" />
                  <p className="mt-2 text-xs font-semibold">
                    {t("profile.role")}
                  </p>
                  <p className="text-sm font-bold">
                    {t(`auth.roles.${user.role}`)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.16 }}
          className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <ProfileStat
            label={t("profile.totalScansTitle")}
            value={
              countQuery.isPending
                ? "…"
                : countQuery.isError
                  ? "—"
                  : totalScans
            }
            icon={ScanLine}
          />
          <ProfileStat
            label={t("profile.memberSince")}
            value={formatDate(user.created_at, i18n.language)}
            icon={Clock3}
          />
          <ProfileStat
            label={t("profile.role")}
            value={t(`auth.roles.${user.role}`)}
            icon={ShieldCheck}
          />
        </motion.section>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.22 }}
          >
            <Card className="h-full border-border/70">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <UserRound className="size-5 text-brand-600 dark:text-brand-400" />
                  {t("profile.detailsTitle")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <dl>
                  <ProfileRow label={t("profile.name")} icon={UserRound}>
                    {user.name}
                  </ProfileRow>
                  <ProfileRow label={t("profile.phone")} icon={Mail}>
                    {user.phone}
                  </ProfileRow>
                  <ProfileRow label={t("profile.email")} icon={Mail}>
                    {user.email ?? (
                      <span className="font-normal text-muted-foreground">—</span>
                    )}
                  </ProfileRow>
                  <ProfileRow label={t("profile.role")} icon={ShieldCheck}>
                    {t(`auth.roles.${user.role}`)}
                  </ProfileRow>
                  <ProfileRow label={t("profile.memberSince")} icon={Clock3}>
                    {formatDate(user.created_at, i18n.language)}
                  </ProfileRow>
                </dl>
              </CardContent>
            </Card>
          </motion.section>

          <motion.section
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.28 }}
          >
            <Card className="h-full border-border/70">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Leaf className="size-5 text-brand-600 dark:text-brand-400" />
                  {t("profile.activityTitle")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="rounded-2xl bg-muted/50 p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        {t("profile.totalScansTitle")}
                      </p>
                      <p className="mt-1 text-3xl font-bold tracking-tight">
                        {countQuery.isPending
                          ? "…"
                          : countQuery.isError
                            ? "—"
                            : totalScans}
                      </p>
                    </div>
                    <span className="flex size-12 items-center justify-center rounded-2xl bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
                      <ScanLine className="size-6" />
                    </span>
                  </div>
                </div>

                <div className="mt-5 flex flex-col gap-3">
                  <Button asChild className="w-full justify-between">
                    <Link to="/scans">
                      <span className="flex items-center gap-2">
                        <History className="size-4" />
                        {t("profile.viewHistory")}
                      </span>
                      <ArrowRight className="size-4" />
                    </Link>
                  </Button>

                  <Button asChild variant="outline" className="w-full justify-between">
                    <Link to="/detect">
                      <span className="flex items-center gap-2">
                        <ScanLine className="size-4" />
                        {t("profile.scanNow")}
                      </span>
                      <ArrowRight className="size-4" />
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.section>
        </div>
      </div>
    </div>
  );
}
