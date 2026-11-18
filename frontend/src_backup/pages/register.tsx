import {
  ShoppingBasket,
  Stethoscope,
  Store,
  Tractor,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { UserRole } from "@/types/auth";
import { cn } from "@/lib/utils";

const ROLES: Array<{ value: UserRole; icon: LucideIcon }> = [
  { value: "farmer", icon: Tractor },
  { value: "customer", icon: ShoppingBasket },
  { value: "expert", icon: Stethoscope },
  { value: "seller", icon: Store },
];

/**
 * Account creation (phone-first). Password and email are optional so a
 * farmer can be up in seconds; a password is added later for password
 * login. Role selects the initial profile type.
 */
export function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuth((state) => state.user);
  const register = useAuth((state) => state.register);
  const loading = useAuth((state) => state.loading);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("farmer");
  const [error, setError] = useState<string | null>(null);

  // Already signed in — nothing to do here.
  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await register({
        name: name.trim(),
        phone,
        role,
        email: email.trim() ? email.trim() : undefined,
        password: password ? password : undefined,
      });
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <AuthShell title={t("auth.registerTitle")} subtitle={t("auth.registerSubtitle")}>
      <form onSubmit={handleSubmit} className="grid gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="grid gap-2">
          <Label>{t("auth.role")}</Label>
          <div role="radiogroup" className="grid grid-cols-2 gap-2">
            {ROLES.map(({ value, icon: Icon }) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={role === value}
                onClick={() => setRole(value)}
                className={cn(
                  "flex flex-col items-center gap-1.5 rounded-lg border p-3 text-sm font-medium transition-colors",
                  role === value
                    ? "border-primary bg-brand-50 text-foreground dark:bg-brand-950"
                    : "border-input text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="size-5" />
                {t(`auth.roles.${value}`)}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-2">
          <Label htmlFor="name">{t("auth.name")}</Label>
          <Input
            id="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            minLength={1}
          />
        </div>

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

        <div className="grid gap-2">
          <Label htmlFor="email">{t("auth.email")}</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="password">{t("auth.passwordOptional")}</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={6}
          />
        </div>

        <Button type="submit" disabled={loading}>
          {t("auth.register")}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        {t("auth.haveAccount")}{" "}
        <Link to="/login" className="font-medium text-primary hover:underline">
          {t("nav.login")}
        </Link>
      </p>
    </AuthShell>
  );
}
