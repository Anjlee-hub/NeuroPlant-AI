import { Outlet } from "react-router-dom";

import { Footer } from "@/components/layout/footer";
import { Header } from "@/components/layout/header";

/**
 * App shell. Sticky header + scrollable main + footer; routes render into
 * <Outlet />. The offline indicator mounts here once the PWA layer lands.
 */
export function RootLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
