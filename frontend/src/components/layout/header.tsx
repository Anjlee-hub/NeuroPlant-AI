import {
  CalendarDays,
  CloudUpload,
  Heart,
  History,
  Home,
  Inbox,
  Landmark,
  Leaf,
  Menu,
  MessageCircle,
  ScanLine,
  ShoppingBag,
  Star,
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

const PRIMARY_NAV_ITEMS: Array<{
  to: string;
  labelKey: string;
  icon: LucideIcon;
  end?: boolean;
}> = [
  { to: "/", labelKey: "nav.home", icon: Home, end: true },
  { to: "/calendar", labelKey: "nav.calendar", icon: CalendarDays },
  { to: "/assistant", labelKey: "nav.assistant", icon: MessageCircle },
  { to: "/marketplace", labelKey: "nav.marketplace", icon: Store },
  { to: "/marketplace/messages", labelKey: "nav.messages", icon: Inbox },
];

const MORE_NAV_ITEMS: Array<{
  to: string;
  labelKey: string;
  icon: LucideIcon;
  end?: boolean;
}> = [
  { to: "/detect", labelKey: "nav.detect", icon: ScanLine },
  { to: "/doctor", labelKey: "nav.doctor", icon: Stethoscope },
  { to: "/scans", labelKey: "nav.history", icon: History },
  { to: "/offline", labelKey: "nav.offlineQueue", icon: CloudUpload },
  { to: "/schemes", labelKey: "nav.schemes", icon: Landmark },
  { to: "/marketplace/browse", labelKey: "nav.marketplaceBuy", icon: ShoppingBag },
  { to: "/marketplace/shop", labelKey: "nav.sellerPortal", icon: Store },
  { to: "/marketplace/products", labelKey: "nav.productMarket", icon: ShoppingBag },
  { to: "/marketplace/favorites", labelKey: "nav.favourites", icon: Heart },
  { to: "/marketplace/my-reviews", labelKey: "nav.myReviews", icon: Star },
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
 * Sticky app header with a compact primary navigation and
 * a More menu for secondary features.
 */
export function Header() {
  const { t } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 print:hidden">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        {/* Logo */}
        <Link
          to="/"
          className="flex shrink-0 items-center gap-2"
          aria-label={t("app.name")}
          onClick={() => setMoreOpen(false)}
        >
          <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Leaf className="size-5" />
          </span>

          <span className="hidden text-lg font-bold tracking-tight sm:inline">
            {t("app.name")}
          </span>
        </Link>

        {/* Desktop navigation */}
        <nav
          className="hidden items-center gap-1 md:flex"
          aria-label="Primary"
        >
          {PRIMARY_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={navClass}
              onClick={() => setMoreOpen(false)}
            >
              <item.icon className="size-4" />
              {t(item.labelKey)}
            </NavLink>
          ))}

          {/* More menu */}
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                "gap-2 text-sm font-medium",
                moreOpen
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
              )}
              aria-expanded={moreOpen}
              aria-haspopup="menu"
              onClick={() => setMoreOpen((open) => !open)}
            >
              {moreOpen ? (
                <X className="size-4" />
              ) : (
                <Menu className="size-4" />
              )}
              More
            </Button>

            {moreOpen && (
              <>
                {/* Backdrop */}
                <button
                  type="button"
                  aria-label="Close menu"
                  className="fixed inset-0 z-40 cursor-default"
                  onClick={() => setMoreOpen(false)}
                />

                {/* Dropdown */}
                <div
                  className="absolute right-0 top-full z-50 mt-2 w-72 rounded-xl border border-border bg-background p-2 shadow-xl"
                  role="menu"
                >
                  <div className="px-3 py-2">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      More Features
                    </p>
                  </div>

                  <div className="grid gap-1">
                    {MORE_NAV_ITEMS.map((item) => (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.end}
                        role="menuitem"
                        className={cn(
                          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                          "text-muted-foreground hover:bg-accent hover:text-foreground",
                        )}
                        onClick={() => setMoreOpen(false)}
                      >
                        <item.icon className="size-4 shrink-0" />
                        {t(item.labelKey)}
                      </NavLink>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </nav>

        {/* Right-side controls */}
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />

          <AuthNav className="hidden md:flex" />

          {/* Mobile menu button */}
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

      {/* Mobile navigation */}
      {mobileOpen && (
        <nav
          className="border-t border-border bg-background px-4 py-4 md:hidden"
          aria-label="Mobile"
        >
          {/* Primary mobile navigation */}
          <div className="grid gap-1">
            {PRIMARY_NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={navClass}
                onClick={() => setMobileOpen(false)}
              >
                <item.icon className="size-4" />
                {t(item.labelKey)}
              </NavLink>
            ))}
          </div>

          {/* More features */}
          <div className="mt-4 border-t border-border pt-4">
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              More Features
            </p>

            <div className="grid gap-1">
              {MORE_NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={navClass}
                  onClick={() => setMobileOpen(false)}
                >
                  <item.icon className="size-4" />
                  {t(item.labelKey)}
                </NavLink>
              ))}
            </div>
          </div>

          {/* Authentication */}
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