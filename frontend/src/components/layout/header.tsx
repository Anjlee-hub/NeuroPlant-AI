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
  PanelLeftClose,
  PanelLeftOpen,
  ScanLine,
  ShoppingBag,
  Star,
  Stethoscope,
  Store,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, useLocation } from "react-router-dom";

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
  { to: "/home", labelKey: "nav.home", icon: Home, end: true },
  { to: "/detect", labelKey: "nav.detect", icon: ScanLine },
  { to: "/scans", labelKey: "nav.history", icon: History },
  { to: "/offline", labelKey: "nav.offlineQueue", icon: CloudUpload },
  { to: "/doctor", labelKey: "nav.doctor", icon: Stethoscope },
  { to: "/calendar", labelKey: "nav.calendar", icon: CalendarDays },
  { to: "/assistant", labelKey: "nav.assistant", icon: MessageCircle },
  { to: "/marketplace", labelKey: "nav.marketplace", icon: Store },
  { to: "/schemes", labelKey: "nav.schemes", icon: Landmark },
  { to: "/community", labelKey: "nav.community", icon: Users },
  { to: "/marketplace/browse", labelKey: "nav.marketplaceBuy", icon: ShoppingBag },
  { to: "/marketplace/shop", labelKey: "nav.sellerPortal", icon: Store },
  { to: "/marketplace/products", labelKey: "nav.productMarket", icon: ShoppingBag },
  { to: "/marketplace/messages", labelKey: "nav.messages", icon: Inbox },
  { to: "/marketplace/favorites", labelKey: "nav.favourites", icon: Heart },
  { to: "/marketplace/my-reviews", labelKey: "nav.myReviews", icon: Star },
];

function SidebarLink({
  item,
  collapsed = false,
  onNavigate,
}: {
  item: (typeof NAV_ITEMS)[number];
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const { t } = useTranslation();

  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      title={collapsed ? t(item.labelKey) : undefined}
      className={({ isActive }) =>
        cn(
          "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
          isActive
            ? "bg-primary text-primary-foreground shadow-sm"
            : "text-muted-foreground hover:bg-accent hover:text-foreground",
          collapsed && "justify-center px-2",
        )
      }
    >
      <item.icon className="size-5 shrink-0" />
      {!collapsed && <span>{t(item.labelKey)}</span>}
    </NavLink>
  );
}

export function Header({
  collapsed,
  onToggleSidebar,
}: {
  collapsed: boolean;
  onToggleSidebar: () => void;
}) {
  const { t } = useTranslation();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const currentPage = [...NAV_ITEMS]
    .sort((a, b) => b.to.length - a.to.length)
    .find((item) =>
      item.end
        ? location.pathname === item.to
        : location.pathname === item.to ||
          location.pathname.startsWith(`${item.to}/`),
    );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 hidden border-r border-border bg-card transition-[width] duration-300 lg:flex lg:flex-col",
          collapsed ? "w-[76px]" : "w-64",
        )}
      >
        <Link
          to="/home"
          className={cn(
            "flex h-16 shrink-0 items-center gap-3 border-b border-border px-5",
            collapsed && "justify-center px-2",
          )}
        >
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Leaf className="size-6" />
          </span>
          {!collapsed && (
            <span className="min-w-0">
              <span className="block truncate text-base font-bold tracking-tight">
                {t("app.name")}
              </span>
              <span className="block text-xs text-muted-foreground">
                Smart crop intelligence
              </span>
            </span>
          )}
        </Link>

        <div className="flex items-center justify-between px-4 pb-2 pt-5">
          {!collapsed && (
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Workspace
            </span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={onToggleSidebar}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" />
            ) : (
              <PanelLeftClose className="size-4" />
            )}
          </Button>
        </div>

        <nav
          className="flex-1 space-y-1 overflow-y-auto px-3 pb-4"
          aria-label="Main navigation"
        >
          {NAV_ITEMS.map((item) => (
            <SidebarLink key={item.to} item={item} collapsed={collapsed} />
          ))}
        </nav>

        {!collapsed && (
          <div className="m-3 rounded-xl border border-border bg-accent/40 p-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Leaf className="size-4 text-primary" />
              Growing smarter
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Better crop insights for healthier harvests.
            </p>
          </div>
        )}
      </aside>

      {/* Top navigation bar */}
      <header
        className={cn(
          "fixed right-0 top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/90 px-4 backdrop-blur-xl transition-[left] duration-300 sm:px-6 print:hidden",
          collapsed ? "lg:left-[76px]" : "lg:left-64",
          "left-0",
        )}
      >
        <div className="flex min-w-0 items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label={t("nav.menu")}
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="size-5" />
          </Button>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold sm:text-base">
              {currentPage ? t(currentPage.labelKey) : t("app.name")}
            </p>
            <p className="hidden text-xs text-muted-foreground sm:block">
              NeuroPlant AI · Smart crop intelligence
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
          <AuthNav className="hidden sm:flex" />
        </div>
      </header>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-[60] lg:hidden print:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />

          <aside className="absolute inset-y-0 left-0 flex w-[min(290px,85vw)] flex-col border-r border-border bg-card shadow-2xl">
            <div className="flex h-16 items-center justify-between border-b border-border px-4">
              <Link
                to="/"
                className="flex items-center gap-2"
                onClick={() => setMobileOpen(false)}
              >
                <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                  <Leaf className="size-5" />
                </span>
                <span className="font-bold">{t("app.name")}</span>
              </Link>

              <Button
                variant="ghost"
                size="icon"
                aria-label="Close navigation"
                onClick={() => setMobileOpen(false)}
              >
                <X className="size-5" />
              </Button>
            </div>

            <nav className="flex-1 space-y-1 overflow-y-auto p-3">
              {NAV_ITEMS.map((item) => (
                <SidebarLink
                  key={item.to}
                  item={item}
                  onNavigate={() => setMobileOpen(false)}
                />
              ))}
            </nav>

            <div className="border-t border-border p-4">
              <AuthNav
                onNavigate={() => setMobileOpen(false)}
                className="flex-col"
              />
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
