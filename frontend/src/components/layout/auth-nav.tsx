import { LogOut, ShieldCheck, User as UserIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/stores/auth";
import { cn } from "@/lib/utils";

interface AuthNavProps {
  /** Fired after a link click so a mobile panel can close itself. */
  onNavigate?: () => void;
  className?: string;
}

/**
 * Header auth entry points. Logged out: login/register links. Logged in:
 * the user's name + logout. `className` lets the mobile panel re-stack it.
 */
export function AuthNav({ onNavigate, className }: AuthNavProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuth((state) => state.user);
  const logout = useAuth((state) => state.logout);

  if (user) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <span className="inline-flex items-center gap-1.5 rounded-md bg-secondary px-3 py-1.5 text-sm font-medium text-secondary-foreground">
          <UserIcon className="size-4 text-muted-foreground" />
          {user.name}
        </span>
        <Button
          asChild
          variant="ghost"
          size="sm"
          aria-label={t("auth.security")}
          onClick={onNavigate}
        >
          <Link to="/settings/mfa">
            <ShieldCheck />
            {t("auth.security")}
          </Link>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={async () => {
            await logout();
            onNavigate?.();
            navigate("/");
          }}
        >
          <LogOut />
          {t("auth.logout")}
        </Button>
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Button asChild variant="ghost" size="sm">
        <Link to="/login" onClick={onNavigate}>
          {t("nav.login")}
        </Link>
      </Button>
      <Button asChild size="sm">
        <Link to="/register" onClick={onNavigate}>
          {t("nav.register")}
        </Link>
      </Button>
    </div>
  );
}
