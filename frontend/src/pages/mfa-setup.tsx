
import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  Copy,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  Smartphone,
} from "lucide-react";


import { motion } from "motion/react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthShell } from "@/components/auth-shell";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { MfaCodesResponse, MfaSetupResponse } from "@/types/auth";

export function MfaSetupPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuth((state) => state.user);

  const [setup, setSetup] = useState<MfaSetupResponse | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!user) navigate("/", { replace: true });
  }, [user, navigate]);

  useEffect(() => {
    let cancelled = false;

    async function loadSetup() {
      try {
        const result = await api.mfaSetup();
        if (!cancelled) setSetup(result);
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    }

    void loadSetup();

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      const result: MfaCodesResponse = await api.mfaConfirm(code);
      setCodes(result.backup_codes);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function copyBackupCodes() {
    if (!codes) return;

    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied(true);
    } catch {
      setError("Unable to copy codes. Please select and copy them manually.");
    }
  }

  return (
    <AuthShell
      title={t("auth.securityTitle")}
      subtitle={t("auth.securitySubtitle")}
    >
      <div className="mx-auto w-full max-w-lg">
        <Link
          to="/"
          className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          {t("nav.home", { defaultValue: "Home" })}
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm"
        >
          <div className="h-1.5 bg-gradient-to-r from-[#123D2B] via-[#218C55] to-emerald-300" />

          <div className="p-5 sm:p-7">
            <div className="mb-6 flex items-center gap-3">
              <span className="flex size-12 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
                <ShieldCheck className="size-6" />
              </span>
              <div>
                <h2 className="text-lg font-bold">
                  {t("auth.securityTitle")}
                </h2>
                <p className="text-xs text-muted-foreground">
                  {t("auth.securitySubtitle")}
                </p>
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="mb-5 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
              >
                {error}
              </div>
            )}

            {codes ? (
              <div className="grid gap-5">
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4">
                  <div className="flex items-center gap-2 font-semibold text-emerald-700 dark:text-emerald-300">
                    <CheckCircle2 className="size-5" />
                    {t("auth.done")}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {t("auth.backupCodesBody")}
                  </p>
                </div>

                <div>
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold">
                      {t("auth.backupCodesBody")}
                    </h3>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => void copyBackupCodes()}
                    >
                      {copied ? (
                        <Check className="size-4" />
                      ) : (
                        <Copy className="size-4" />
                      )}
                      {copied ? "Copied" : "Copy codes"}
                    </Button>
                  </div>

                  <ul className="grid grid-cols-2 gap-2">
                    {codes.map((backup) => (
                      <li
                        key={backup}
                        className="rounded-lg border border-border bg-muted/60 px-3 py-3 text-center font-mono text-sm font-semibold tracking-wide"
                      >
                        {backup}
                      </li>
                    ))}
                  </ul>
                </div>

                <p className="text-xs leading-5 text-muted-foreground">
                  Store these backup codes somewhere secure. Each code should
                  be treated as a recovery credential.
                </p>

                <Button
                  className="h-11 w-full"
                  onClick={() => navigate("/", { replace: true })}
                >
                  <CheckCircle2 className="size-4" />
                  {t("auth.done")}
                </Button>
              </div>
            ) : setup ? (
              <div className="grid gap-6">
                <div className="grid gap-3">
                  <div className="flex items-center gap-2">
                    <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      1
                    </span>
                    <h3 className="text-sm font-semibold">
                      Set up your authenticator
                    </h3>
                  </div>

                  <p className="text-sm leading-6 text-muted-foreground">
                    Scan this QR code using an authenticator application on
                    your phone.
                  </p>

                  <div className="flex flex-col items-center rounded-xl border border-border bg-white p-5">
                    <img
                      src={setup.qr_url}
                      alt="Authenticator setup QR code"
                      className="size-48 rounded-lg object-contain"
                    />
                    <p className="mt-3 text-center text-xs text-gray-500">
                      {t("auth.mfaQrHint")}
                    </p>
                  </div>
                </div>

                <div className="grid gap-3">
                  <div className="flex items-center gap-2">
                    <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      2
                    </span>
                    <h3 className="text-sm font-semibold">
                      Enter the setup key
                    </h3>
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="mfa-secret">
                      {t("auth.mfaSecret")}
                    </Label>
                    <Input
                      id="mfa-secret"
                      value={setup.secret}
                      readOnly
                      onFocus={(event) => event.currentTarget.select()}
                      className="h-11 rounded-lg font-mono text-sm"
                    />
                    <p className="text-xs text-muted-foreground">
                      Keep this secret private. Anyone with this key may be
                      able to generate authentication codes.
                    </p>
                  </div>

                  <a
                    href={setup.otpauth_uri}
                    className="break-all text-xs text-primary underline-offset-4 hover:underline"
                  >
                    Open authenticator setup link
                  </a>
                </div>

                <form onSubmit={handleConfirm} className="grid gap-4">
                  <div className="flex items-center gap-2">
                    <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      3
                    </span>
                    <h3 className="text-sm font-semibold">
                      Verify your authenticator
                    </h3>
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="confirm-code">
                      {t("auth.mfaCode")}
                    </Label>
                    <div className="relative">
                      <KeyRound className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="confirm-code"
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
                        className="h-12 rounded-xl pl-10 text-center text-lg tracking-[0.5em]"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Enter the six-digit code displayed in your authenticator
                      application.
                    </p>
                  </div>

                  <Button
                    type="submit"
                    disabled={busy || code.length !== 6}
                    className="h-12 w-full rounded-xl"
                  >
                    {busy ? (
                      <LoaderCircle className="size-4 animate-spin" />
                    ) : (
                      <LockKeyhole className="size-4" />
                    )}
                    {busy ? t("common.loading") : t("auth.confirmMfa")}
                  </Button>
                </form>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 py-12 text-center">
                {error ? (
                  <ShieldCheck className="size-10 text-destructive" />
                ) : (
                  <LoaderCircle className="size-10 animate-spin text-primary" />
                )}
                <p className="text-sm text-muted-foreground">
                  {error ?? t("common.loading")}
                </p>
                {error && (
                  <Button
                    variant="outline"
                    onClick={() => window.location.reload()}
                  >
                    Try again
                  </Button>
                )}
              </div>
            )}
          </div>
        </motion.div>

        <div className="mt-5 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <Smartphone className="size-4" />
          <span>{t("auth.securityTitle")}</span>
        </div>
      </div>
    </AuthShell>
  );
}
