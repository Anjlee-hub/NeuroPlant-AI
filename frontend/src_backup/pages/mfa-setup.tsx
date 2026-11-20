import { ShieldCheck } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { MfaCodesResponse, MfaSetupResponse } from "@/types/auth";

/**
 * Enroll an authenticator (TOTP). Sequence: fetch provisioning data →
 * user scans the QR / enters the secret → confirm a code → backup codes
 * are shown exactly once.
 */
export function MfaSetupPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuth((state) => state.user);

  const [setup, setSetup] = useState<MfaSetupResponse | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Auth-required.
  useEffect(() => {
    if (!user) navigate("/", { replace: true });
  }, [user, navigate]);

  // Provision the TOTP secret once on entry.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const result = await api.mfaSetup();
        if (!cancelled) setSetup(result);
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleConfirm(event: FormEvent) {
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

  return (
    <AuthShell title={t("auth.securityTitle")} subtitle={t("auth.securitySubtitle")}>
      {codes ? (
        <div className="grid gap-4">
          <p className="text-sm text-muted-foreground">{t("auth.backupCodesBody")}</p>
          <ul className="grid grid-cols-2 gap-2">
            {codes.map((backup) => (
              <li
                key={backup}
                className="rounded-md bg-muted px-3 py-2 text-center font-mono text-sm"
              >
                {backup}
              </li>
            ))}
          </ul>
          <Button onClick={() => navigate("/")}>{t("auth.done")}</Button>
        </div>
      ) : setup ? (
        <form onSubmit={handleConfirm} className="grid gap-4">
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="grid justify-items-center gap-3">
            <img
              src={setup.qr_url}
              alt="TOTP QR code"
              className="size-40 rounded-lg border border-border"
            />
            <p className="text-xs text-muted-foreground">{t("auth.mfaQrHint")}</p>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="secret">{t("auth.mfaSecret")}</Label>
            <Input
              id="secret"
              readOnly
              value={setup.secret}
              onFocus={(event) => event.currentTarget.select()}
            />
            <a
              href={setup.otpauth_uri}
              className="text-center text-xs text-primary hover:underline"
            >
              {setup.otpauth_uri.split("?")[0]}
            </a>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="confirm-code">{t("auth.mfaCode")}</Label>
            <Input
              id="confirm-code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              pattern="[0-9]{6}"
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
              required
            />
          </div>
          <Button type="submit" disabled={busy || code.length !== 6}>
            <ShieldCheck />
            {t("auth.confirmMfa")}
          </Button>
        </form>
      ) : (
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      )}
    </AuthShell>
  );
}
