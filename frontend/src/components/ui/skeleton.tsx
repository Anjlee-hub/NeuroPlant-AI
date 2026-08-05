import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Shimmer-free pulse placeholder used while async content loads. */
function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  );
}

export { Skeleton };
