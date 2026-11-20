
import {
  ArrowRight,
  Check,
  Leaf,
  LoaderCircle,
  Mail,
  Phone,
  ShieldCheck,
  ShoppingBasket,
  Sprout,
  Stethoscope,
  Store,
  Tractor,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

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

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      await register({
        name: name.trim(),
        phone: phone.trim(),
        role,
        email: email.trim() ? email.trim() : undefined,
        password: password || undefined,
      });

      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section className="relative flex min-h-[calc(100dvh-12rem)] items-center justify-center overflow-hidden bg-background px-4 py-10 sm:px-6 lg:py-14">
      <div className="pointer-events-none absolute -left-24 top-10 size-72 rounded-full bg-emerald-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-28 -right-20 size-96 rounded-full bg-lime-500/10 blur-3xl" />

      <div className="relative mx-auto grid w-full max-w-5xl overflow-hidden rounded-3xl border border-border/70 bg-card shadow-xl lg:grid-cols-[0.9fr_1.1fr]">
        <motion.aside
          initial={{ opacity: 0, x: -18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.45 }}
          className="relative hidden min-h-[720px] flex-col justify-between overflow-hidden bg-gradient-to-br from-[#123D2B] via-[#17633D] to-[#218C55] p-10 text-white lg:flex"
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
              {t("auth.registerTitle")}
            </h2>

            <p className="mt-4 text-sm leading-7 text-emerald-50/85">
              {t("auth.registerSubtitle")}
            </p>

            <div className="mt-9 space-y-5">
              <div className="flex items-start gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-white/10">
                  <Sprout className="size-4" />
                </span>
                <div>
                  <p className="text-sm font-semibold">
                    {t("auth.roles.farmer")}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-emerald-50/75">
                    AI-assisted crop health support
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-white/10">
                  <ShieldCheck className="size-4" />
                </span>
                <div>
                  <p className="text-sm font-semibold">
                    {t("auth.securityTitle")}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-emerald-50/75">
                    Your account and farming activity in one place
                  </p>
                </div>
              </div>
            </div>
          </div>

          <p className="relative z-10 text-xs text-emerald-100/70">
            {t("app.name")}
          </p>
        </motion.aside>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.08 }}
          className="flex items-center justify-center p-5 sm:p-9 lg:p-10"
        >
          <div className="w-full max-w-md">
            <Link to="/" className="mb-7 inline-flex items-center gap-2 lg:hidden">
              <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <Leaf className="size-5" />
              </span>
              <span className="text-lg font-bold">{t("app.name")}</span>
            </Link>

            <div className="mb-7">
              <p className="mb-2 text-sm font-semibold text-primary">
                {t("auth.role")}
              </p>
              <h1 className="text-3xl font-bold tracking-tight">
                {t("auth.registerTitle")}
              </h1>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {t("auth.registerSubtitle")}
              </p>
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

              <fieldset>
                <legend className="mb-3 text-sm font-medium">
                  {t("auth.role")}
                </legend>

                <div
                  role="radiogroup"
                  aria-label={t("auth.role")}
                  className="grid grid-cols-2 gap-2"
                >
                  {ROLES.map(({ value, icon: Icon }) => {
                    const selected = role === value;

                    return (
                      <button
                        key={value}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        onClick={() => setRole(value)}
                        className={cn(
                          "group relative flex min-h-24 flex-col items-center justify-center gap-2 rounded-xl border p-3 text-sm font-medium transition-all duration-200",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                          selected
                            ? "border-primary bg-brand-50 text-brand-800 shadow-sm dark:bg-brand-950/50 dark:text-brand-200"
                            : "border-border bg-background text-muted-foreground hover:border-primary/50 hover:bg-muted/50 hover:text-foreground",
                        )}
                      >
                        {selected && (
                          <span className="absolute right-2 top-2 flex size-5 items-center justify-center rounded-full bg-primary text-primary-foreground">
                            <Check className="size-3" />
                          </span>
                        )}
                        <Icon
                          className={cn(
                            "size-6 transition-transform duration-200 group-hover:scale-110",
                            selected && "text-primary",
                          )}
                        />
                        <span>{t(`auth.roles.${value}`)}</span>
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <div className="grid gap-2">
                <Label htmlFor="register-name">{t("auth.name")}</Label>
                <div className="relative">
                  <UserRound className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="register-name"
                    type="text"
                    autoComplete="name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                    minLength={1}
                    maxLength={100}
                    className="h-11 rounded-xl pl-10"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="register-phone">{t("auth.phone")}</Label>
                <div className="relative">
                  <Phone className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="register-phone"
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    required
                    className="h-11 rounded-xl pl-10"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="register-email">{t("auth.email")}</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="register-email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="h-11 rounded-xl pl-10"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="register-password">
                  {t("auth.passwordOptional")}
                </Label>
                <Input
                  id="register-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={6}
                  className="h-11 rounded-xl"
                />
                <p className="text-xs text-muted-foreground">
                  Leave blank if you prefer phone-based login.
                </p>
              </div>

              <Button
                type="submit"
                disabled={loading || !name.trim() || !phone.trim()}
                className="mt-1 h-12 w-full rounded-xl"
              >
                {loading ? (
                  <LoaderCircle className="size-4 animate-spin" />
                ) : (
                  <ArrowRight className="size-4" />
                )}
                {t("auth.register")}
              </Button>
            </form>

            <p className="mt-7 text-center text-sm text-muted-foreground">
              {t("auth.haveAccount")}{" "}
              <Link
                to="/login"
                className="font-semibold text-primary underline-offset-4 hover:underline"
              >
                {t("nav.login")}
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
