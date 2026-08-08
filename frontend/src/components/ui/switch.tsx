import * as React from "react";

import { cn } from "@/lib/utils";

const Switch = React.forwardRef<
  HTMLInputElement,
  React.ComponentProps<"input"> & {
    label?: string;
    description?: string;
    id?: string;
  }
>(({ className, label, description, id: propId, ...props }, ref) => {
  const generatedId = React.useId();
  const switchId = propId ?? generatedId;
  const labelId = `${switchId}-label`;
  const descId = description ? `${switchId}-desc` : undefined;

  return (
    <div className="flex items-start gap-3">
      <label htmlFor={switchId} className="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          id={switchId}
          ref={ref}
          className={cn(
            "h-4 w-4 shrink-0 rounded border-2 border-input bg-background checked:bg-primary checked:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors",
            className,
          )}
          aria-describedby={descId}
          {...props}
        />
        {label && (
          <span id={labelId} className="text-sm font-medium">
            {label}
          </span>
        )}
      </label>
      {description && (
        <p id={descId} className="text-xs text-muted-foreground mt-1">
          {description}
        </p>
      )}
    </div>
  );
});
Switch.displayName = "Switch";

export { Switch };