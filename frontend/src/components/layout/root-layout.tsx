
import { useState } from "react";
import { Outlet } from "react-router-dom";

import { Footer } from "@/components/layout/footer";
import { Header } from "@/components/layout/header";
import { OfflineIndicator } from "@/components/offline-indicator";

export function RootLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header
        collapsed={sidebarCollapsed}
        onToggleSidebar={() =>
          setSidebarCollapsed((previous) => !previous)
        }
      />

      <div
        className={`flex min-h-screen flex-col pt-16 transition-[padding] duration-300 ${
          sidebarCollapsed ? "lg:pl-[76px]" : "lg:pl-64"
        }`}
      >
        <main className="min-w-0 flex-1">
          <Outlet />
        </main>

        <Footer />
      </div>

      <OfflineIndicator />
    </div>
  );
}
