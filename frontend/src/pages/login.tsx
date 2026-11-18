
import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Leaf,
  LoaderCircle,
  LockKeyhole,
  Phone,
  ShieldCheck,
  Sprout,
} from "lucide-react";
import { motion } from "motion/react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { cn } from "@/lib/utils";

type Mode = "password" | "otp";

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const user = useAuth((state) => state.user);
  const login = useAuth((state) => state.login);
  const sendOtp = useAuth((state) => state.sendOtp);
  const verifyOtp = useAuth((state) => state.verifyOtp);
  const loading = useAuth((state) => state.loading);

  const [mode, setMode] = useState<Mode>("password");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const outcome = await login(identifier.trim(), password);
      navigate(outcome === "mfa" ? "/login/mfa" : "/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleSendOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const result = await sendOtp(phone.trim());
      setDebugCode(result);
      setOtpSent(true);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleVerifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      await verifyOtp(phone.trim(), code);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function changeMode(nextMode: Mode) {
    setMode(nextMode);
    setError(null);
    setCode("");
    setOtpSent(false);
    setDebugCode(null);
  }

  return (
    <section className="relative flex min-h-[calc(100dvh-12rem)] items-center justify-center overflow-hidden bg-background px-4 py-10 sm:px-6 lg:py-14">
      <div className="pointer-events-none absolute -left-28 top-10 size-72 rounded-full bg-emerald-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-20 size-96 rounded-full bg-lime-500/10 blur-3xl" />

      <div className="relative mx-auto grid w-full max-w-5xl overflow-hidden rounded-3xl border border-border/70 bg-card shadow-xl lg:grid-cols-[0.95fr_1.05fr]">
        <motion.aside
          initial={{ opacity: 0, x: -18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.45 }}
          className="relative hidden min-h-[620px] flex-col justify-between overflow-hidden bg-gradient-to-br from-[#123D2B] via-[#17633D] to-[#218C55] p-10 text-white lg:flex"
        >
          <div className="absolute -right-24 top-24 size-72 rounded-full border border-white/10" />
          <div className="absolute -right-12 top-36 size-48 rounded-full border border-white/10" />
          <div className="absolute -bottom-28 -left-16 size-80 rounded-full bg-white/5" />

          <Link to="/" className="relative z-10 inline-flex items-center gap-3">
            <span className="flex size-11 items-center justify-center rounded-xl bg-white/15 ring-1 ring-white/20">
              <Leaf className="size-6" />
            </span>
            <span className="text-xl font-bold tracking-tight">
              {t("app.name")}
            </span>
          </Link>

          <div className="relative z-10 max-w-sm">
            <div className="mb-6 flex size-16 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/20">
              <Sprout className="size-9" />
            </div>
            <h2 className="text-3xl font-bold leading-tight xl:text-4xl">
              {t("auth.loginTitle")}
            </h2>
            <p className="mt-4 text-sm leading-7 text-emerald-50/85">
              {t("auth.loginSubtitle")}
            </p>

            <div className="mt-9 space-y-4">
              {[
                t("auth.loginBenefit1", { defaultValue: "AI-powered crop health insights" }),
                t("auth.loginBenefit2", { defaultValue: "Track scans and treatment progress" }),
                t("auth.loginBenefit3", { defaultValue: "Practical guidance for your farm" }),
              ].map((item) => (
                <div key={item} className="flex items-center gap-3 text-sm text-emerald-50">
                  <CheckCircle2 className="size-5 shrink-0 text-emerald-200" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="relative z-10 text-xs text-emerald-100/70">
            {t("app.name")} · {t("auth.loginMethod")}
          </p>
        </motion.aside>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.08 }}
          className="flex items-center justify-center p-5 sm:p-9 lg:p-12"
        >
          <div className="w-full max-w-md">
            <Link to="/" className="mb-8 inline-flex items-center gap-2 lg:hidden">
              <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <Leaf className="size-5" />
              </span>
              <span className="text-lg font-bold">{t("app.name")}</span>
            </Link>

            <div className="mb-8">
              <p className="mb-2 text-sm font-semibold text-primary">
                {t("auth.loginMethod")}
              </p>
              <h1 className="text-3xl font-bold tracking-tight">
                {t("auth.loginTitle")}
              </h1>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {t("auth.loginSubtitle")}
              </p>
            </div>

            <div
              role="tablist"
              aria-label={t("auth.loginMethod")}
              className="mb-6 grid grid-cols-2 gap-1 rounded-xl bg-muted p-1"
              onKeyDown={(event) => {
                if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
                event.preventDefault();
                changeMode(mode === "password" ? "otp" : "password");
              }}
            >
              <button
                id="login-tab-password"
                type="button"
                role="tab"
                aria-selected={mode === "password"}
                aria-controls="login-panel"
                onClick={() => changeMode("password")}
                className={cn(
                  "flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-semibold transition-all",
                  mode === "password"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <LockKeyhole className="size-4" />
                {t("auth.passwordLogin")}
              </button>

              <button
                id="login-tab-otp"
                type="button"
                role="tab"
                aria-selected={mode === "otp"}
                aria-controls="login-panel"
                onClick={() => changeMode("otp")}
                className={cn(
                  "flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-semibold transition-all",
                  mode === "otp"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Phone className="size-4" />
                {t("auth.otpLogin")}
              </button>
            </div>

            <div
              id="login-panel"
              role="tabpanel"
              aria-labelledby={`login-tab-${mode}`}
            >
              {error && (
                <div
                  role="alert"
                  className="mb-5 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
                >
                  {error}
                </div>
              )}

              {mode === "password" ? (
                <form onSubmit={handlePasswordSubmit} className="grid gap-5">
                  <div className="grid gap-2">
                    <Label htmlFor="identifier">{t("auth.identifier")}</Label>
                    <Input
                      id="identifier"
                      type="text"
                      autoComplete="username"
                      placeholder={t("auth.identifier")}
                      value={identifier}
                      onChange={(event) => setIdentifier(event.target.value)}
                      required
                      minLength={3}
                      className="h-12 rounded-xl"
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="password">{t("auth.password")}</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      required
                      className="h-12 rounded-xl"
                    />
                  </div>

                  <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl">
                    {loading ? (
                      <LoaderCircle className="size-4 animate-spin" />
                    ) : (
                      <ArrowRight className="size-4" />
                    )}
                    {t("auth.login")}
                  </Button>
                </form>
              ) : otpSent ? (
                <form onSubmit={handleVerifyOtp} className="grid gap-5">
                  <div className="rounded-xl bg-muted/60 p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      <ShieldCheck className="size-4 text-primary" />
                      {t("auth.otpSent", { phone })}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t("auth.otpCode")}
                    </p>
                  </div>

                  {debugCode && (
                    <p className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-muted-foreground">
                      {t("auth.otpDebugHint", { code: debugCode })}
                    </p>
                  )}

                  <div className="grid gap-2">
                    <Label htmlFor="otp">{t("auth.otpCode")}</Label>
                    <Input
                      id="otp"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      maxLength={6}
                      pattern="[0-9]{6}"
                      placeholder="000000"
                      value={code}
                      onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
                      required
                      className="h-12 rounded-xl text-center text-xl tracking-[0.5em]"
                    />
                  </div>

                  <Button
                    type="submit"
                    disabled={loading || code.length !== 6}
                    className="h-12 w-full rounded-xl"
                  >
                    {loading ? <LoaderCircle className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
                    {t("auth.verifyOtp")}
                  </Button>

                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full"
                    onClick={() => {
                      setOtpSent(false);
                      setCode("");
                      setError(null);
                    }}
                  >
                    <ArrowLeft className="size-4" />
                    {t("common.back", { defaultValue: "Change phone number" })}
                  </Button>
                </form>
              ) : (
                <form onSubmit={handleSendOtp} className="grid gap-5">
                  <div className="grid gap-2">
                    <Label htmlFor="phone">{t("auth.phone")}</Label>
                    <Input
                      id="phone"
                      type="tel"
                      inputMode="tel"
                      autoComplete="tel"
                      placeholder={t("auth.phone")}
                      value={phone}
                      onChange={(event) => setPhone(event.target.value)}
                      required
                      className="h-12 rounded-xl"
                    />
                  </div>

                  <Button type="submit" disabled={loading} className="h-12 w-full rounded-xl">
                    {loading ? (
                      <LoaderCircle className="size-4 animate-spin" />
                    ) : (
                      <Phone className="size-4" />
                    )}
                    {t("auth.sendOtp")}
                  </Button>
                </form>
              )}
            </div>

            <div className="my-7 flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground">
                {t("auth.noAccount")}
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <p className="text-center text-sm text-muted-foreground">
              {t("auth.noAccount")}{" "}
              <Link
                to="/register"
                className="font-semibold text-primary underline-offset-4 hover:underline"
              >
                {t("nav.register")}
              </Link>
            </p>

            <div className="mt-7 flex items-center justify-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="size-4" />
              {t("auth.securityTitle")}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
