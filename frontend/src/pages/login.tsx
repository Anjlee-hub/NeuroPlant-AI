import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import { cn } from "@/lib/utils";

type Mode = "password" | "otp";

/**
 * Login with either a password (phone/email) or a phone OTP. When the
 * account has MFA enabled the API answers with a challenge and we route
 * to /login/mfa.
 */
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

  // Already signed in — nothing to do here.
  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  async function handlePasswordSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const outcome = await login(identifier, password);
      navigate(outcome === "mfa" ? "/login/mfa" : "/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleSendOtp(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const dbg = await sendOtp(phone);
      setDebugCode(dbg);
      setOtpSent(true);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleVerifyOtp(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await verifyOtp(phone, code);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <AuthShell title={t("auth.loginTitle")} subtitle={t("auth.loginSubtitle")}>
      <div
        role="tablist"
        className="mb-6 grid grid-cols-2 gap-1 rounded-lg bg-muted p-1"
        aria-label="Login method"
      >
        {(["password", "otp"] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={mode === value}
            onClick={() => {
              setMode(value);
              setError(null);
            }}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              mode === value
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {value === "password" ? t("auth.passwordLogin") : t("auth.otpLogin")}
          </button>
        ))}
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {mode === "password" ? (
        <form onSubmit={handlePasswordSubmit} className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="identifier">{t("auth.identifier")}</Label>
            <Input
              id="identifier"
              type="text"
              autoComplete="username"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              required
              minLength={3}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password">{t("auth.password")}</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={loading}>
            {t("auth.login")}
          </Button>
        </form>
      ) : otpSent ? (
        <form onSubmit={handleVerifyOtp} className="grid gap-4">
          <p className="text-sm text-muted-foreground">
            {t("auth.otpSent", { phone })}
          </p>
          {debugCode && (
            <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
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
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
              required
            />
          </div>
          <Button type="submit" disabled={loading || code.length !== 6}>
            {t("auth.verifyOtp")}
          </Button>
        </form>
      ) : (
        <form onSubmit={handleSendOtp} className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="phone">{t("auth.phone")}</Label>
            <Input
              id="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={loading}>
            {t("auth.sendOtp")}
          </Button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-muted-foreground">
        {t("auth.noAccount")}{" "}
        <Link to="/register" className="font-medium text-primary hover:underline">
          {t("nav.register")}
        </Link>
      </p>
    </AuthShell>
  );
}
