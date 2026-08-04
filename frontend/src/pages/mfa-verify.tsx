import { ShieldCheck } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";

/**
 * Second factor for accounts with MFA enabled. The login endpoint stashed
 * a challenge in the auth store; verifying it here exchanges it for a full
 * token pair.
 */
export function MfaVerifyPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const challenge = useAuth((state) => state.challenge);
  const verifyMfa = useAuth((state) => state.verifyMfa);
  const loading = useAuth((state) => state.loading);

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  // No pending challenge (e.g. page refreshed mid-login) → back to login.
  useEffect(() => {
    if (!challenge) navigate("/login", { replace: true });
  }, [challenge, navigate]);

  async function handleSubmit(event: FormEvent) {
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
    <AuthShell title={t("auth.mfaTitle")} subtitle={t("auth.mfaSubtitle")}>
      <form onSubmit={handleSubmit} className="grid gap-4">
        <div className="flex justify-center py-2">
          <span className="flex size-12 items-center justify-center rounded-full bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
            <ShieldCheck className="size-6" />
          </span>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="grid gap-2">
          <Label htmlFor="mfa-code">{t("auth.mfaCode")}</Label>
          <Input
            id="mfa-code"
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
          {t("auth.mfaVerify")}
        </Button>
      </form>
    </AuthShell>
  );
}
