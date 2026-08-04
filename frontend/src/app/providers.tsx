import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { ThemeProvider } from "@/app/theme-provider";

/**
 * App-wide providers, ordered outside-in:
 * React Query (server cache) -> Theme (class-based dark mode).
 * Router and i18n are mounted at the top level (main.tsx / App.tsx).
 */
export function Providers({ children }: { children: ReactNode }) {
  // One QueryClient per app lifecycle (staleTime tuned for a mobile-first,
  // data-light shell; per-query overrides land as features are added).
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
}
