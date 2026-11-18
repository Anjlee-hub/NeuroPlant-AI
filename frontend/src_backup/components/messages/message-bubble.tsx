import { CheckCheck } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { Message } from "@/types/messages";

/** Timestamp shown inside a bubble (e.g. "14:05"). */
function bubbleTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * One message bubble (M4 Task 5). The caller's own messages are right-aligned
 * and filled; the other side's are left-aligned. A read receipt (double-check
 * with an aria-label) appears under the caller's sent messages once the other
 * side has read them.
 */
export function MessageBubble({
  message,
  isOwn,
}: {
  message: Message;
  isOwn: boolean;
}) {
  const { t } = useTranslation();

  if (isOwn) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
          <p className="whitespace-pre-wrap">{message.content}</p>
          <span className="mt-1 flex items-center justify-end gap-1 text-[10px] font-normal opacity-70">
            {bubbleTime(message.created_at)}
            {message.read_at && (
              <CheckCheck
                className="size-3"
                role="img"
                aria-label={t("messages.read")}
              />
            )}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm border bg-background px-4 py-2.5 text-sm">
        <p className="whitespace-pre-wrap">{message.content}</p>
        <span className="mt-1 block text-right text-[10px] text-muted-foreground/70">
          {bubbleTime(message.created_at)}
        </span>
      </div>
    </div>
  );
}
