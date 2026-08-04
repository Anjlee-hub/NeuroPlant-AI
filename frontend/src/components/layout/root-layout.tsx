import { Outlet } from "react-router-dom";

import { Footer } from "@/components/layout/footer";
import { Header } from "@/components/layout/header";
import { OfflineIndicator } from "@/components/offline-indicator";

/**
 * App shell. Sticky header + scrollable main + footer; routes render into
 * <Outlet />. The offline indicator floats above the footer when offline.
 */
export function RootLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <OfflineIndicator />
    </div>
  );
}
