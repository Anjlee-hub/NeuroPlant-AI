import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Centered icon + title + body + action card used by every feature page for
 * its non-content states (empty, error, sign-in-required). Keeping them in one
 * component keeps those states visually identical across the app.
 */
export function StateCard({
  icon: Icon,
  title,
  body,
  tone = "default",
  className,
  children,
}: {
  icon: LucideIcon;
  title: string;
  body?: string;
  /** "destructive" tints the icon to signal an error. */
  tone?: "default" | "destructive";
  className?: string;
  /** Optional action (button/link) rendered under the body. */
  children?: ReactNode;
}) {
  return (
    <Card className={className}>
      <CardContent className="flex flex-col items-center gap-4 p-10 text-center">
        <Icon
          className={cn(
            "size-10",
            tone === "destructive" ? "text-destructive" : "text-muted-foreground",
          )}
        />
        <h3 className="text-lg font-semibold">{title}</h3>
        {body && <p className="text-sm text-muted-foreground">{body}</p>}
        {children}
      </CardContent>
    </Card>
  );
}
