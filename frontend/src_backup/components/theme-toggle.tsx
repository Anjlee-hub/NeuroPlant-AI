import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/app/theme-provider";
import { Button } from "@/components/ui/button";

/**
 * Flips between light and dark. First click pins the preference explicitly
 * (defaults to following the OS via "system" until the user chooses).
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {isDark ? <Sun /> : <Moon />}
    </Button>
  );
}
