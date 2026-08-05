import {
  History,
  Home,
  Leaf,
  Menu,
  ScanLine,
  Stethoscope,
  Store,
  X,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink } from "react-router-dom";

import { AuthNav } from "@/components/layout/auth-nav";
import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_ITEMS: Array<{
  to: string;
  labelKey: string;
  icon: LucideIcon;
  end?: boolean;
}> = [
  { to: "/", labelKey: "nav.home", icon: Home, end: true },
  { to: "/detect", labelKey: "nav.detect", icon: ScanLine },
  { to: "/scans", labelKey: "nav.history", icon: History },
  { to: "/doctor", labelKey: "nav.doctor", icon: Stethoscope },
  { to: "/marketplace", labelKey: "nav.marketplace", icon: Store },
];

function navClass({ isActive }: { isActive: boolean }) {
  return cn(
    "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-accent text-accent-foreground"
      : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
  );
}

/**
 * Sticky app header: brand, primary navigation, language + theme controls,
 * and auth entry points. Collapses to a slide-down panel on small screens.
 */
export function Header() {
  const { t } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link
          to="/"
          className="flex shrink-0 items-center gap-2"
          aria-label={t("app.name")}
        >
          <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Leaf className="size-5" />
          </span>
          <span className="hidden text-lg font-bold tracking-tight sm:inline">
            {t("app.name")}
          </span>
        </Link>

        {/* Desktop navigation */}
        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={navClass}
            >
              <item.icon className="size-4" />
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />

          <AuthNav className="hidden md:flex" />

          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            aria-label={t("nav.menu")}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((open) => !open)}
          >
            {mobileOpen ? <X /> : <Menu />}
          </Button>
        </div>
      </div>

      {/* Mobile panel */}
      {mobileOpen && (
        <nav
          className="border-t border-border px-4 py-4 md:hidden"
          aria-label="Mobile"
        >
          <ul className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={navClass}
                  onClick={() => setMobileOpen(false)}
                >
                  <item.icon className="size-4" />
                  {t(item.labelKey)}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-col gap-2 border-t border-border pt-4">
            <AuthNav
              onNavigate={() => setMobileOpen(false)}
              className="flex-col"
            />
          </div>
        </nav>
      )}
    </header>
  );
}
