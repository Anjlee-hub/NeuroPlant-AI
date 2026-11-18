
import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  KeyRound,
  Leaf,
  LoaderCircle,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import { motion } from "motion/react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";

export function MfaVerifyPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const challenge = useAuth((state) => state.challenge);
  const verifyMfa = useAuth((state) => state.verifyMfa);
  const loading = useAuth((state) => state.loading);

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!challenge) {
      navigate("/login", { replace: true });
    }
  }, [challenge, navigate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      await verifyMfa(code);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="relative flex min-h-[calc(100dvh-12rem)] items-center justify-center overflow-hidden bg-background px-4 py-12">
      <div className="pointer-events-none absolute -left-24 top-10 size-72 rounded-full bg-emerald-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-28 -right-20 size-96 rounded-full bg-lime-500/10 blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative w-full max-w-md"
      >
        <Link
          to="/login"
          className="mb-7 inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          {t("nav.login")}
        </Link>

        <div className="overflow-hidden rounded-3xl border border-border/70 bg-card shadow-xl">
          <div className="h-2 bg-gradient-to-r from-[#123D2B] via-[#218C55] to-emerald-300" />

          <div className="p-6 sm:p-9">
            <Link
              to="/"
              className="mb-8 inline-flex items-center gap-2"
              aria-label={t("app.name")}
            >
              <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <Leaf className="size-5" />
              </span>
              <span className="text-lg font-bold tracking-tight">
                {t("app.name")}
              </span>
            </Link>

            <div className="mb-7">
              <div className="mb-5 flex size-14 items-center justify-center rounded-2xl bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
                <ShieldCheck className="size-7" />
              </div>

              <p className="mb-2 text-sm font-semibold text-primary">
                {t("auth.securityTitle")}
              </p>
              <h1 className="text-3xl font-bold tracking-tight">
                {t("auth.mfaTitle")}
              </h1>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {t("auth.mfaSubtitle")}
              </p>
            </div>

            <div className="mb-6 flex items-start gap-3 rounded-xl border border-border/70 bg-muted/40 p-4">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-background text-primary shadow-sm">
                <Smartphone className="size-4" />
              </span>
              <div>
                <p className="text-sm font-semibold">
                  {t("auth.mfaCode")}
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Enter the six-digit code from your authenticator app.
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="grid gap-5">
              {error && (
                <div
                  role="alert"
                  className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
                >
                  {error}
                </div>
              )}

              <div className="grid gap-2">
                <Label htmlFor="mfa-code">
                  {t("auth.mfaCode")}
                </Label>
                <div className="relative">
                  <KeyRound className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="mfa-code"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    pattern="[0-9]{6}"
                    placeholder="000000"
                    value={code}
                    onChange={(event) =>
                      setCode(event.target.value.replace(/\D/g, ""))
                    }
                    required
                    autoFocus
                    className="h-14 rounded-xl pl-10 text-center text-xl font-semibold tracking-[0.6em]"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Enter all six digits to continue.
                </p>
              </div>

              <Button
                type="submit"
                disabled={loading || code.length !== 6}
                className="h-12 w-full rounded-xl"
              >
                {loading ? (
                  <LoaderCircle className="size-4 animate-spin" />
                ) : (
                  <ArrowRight className="size-4" />
                )}
                {t("auth.mfaVerify")}
              </Button>
            </form>

            <div className="mt-7 flex items-center justify-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="size-4" />
              {t("auth.securityTitle")}
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
