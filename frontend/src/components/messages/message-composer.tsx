import { Send } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MESSAGE_MAX_LENGTH } from "@/types/messages";

/**
 * Message composer (M4 Task 5). Enter sends, Shift+Enter adds a newline. The
 * textarea is disabled while sending or once the thread is closed; a live
 * character counter keeps the backend's 2000-char limit visible.
 */
export function MessageComposer({
  disabled,
  onSend,
  autoFocus,
}: {
  disabled: boolean;
  onSend: (content: string) => void;
  autoFocus?: boolean;
}) {
  const { t } = useTranslation();
  const [content, setContent] = useState("");

  const trimmed = content.trim();
  const canSend = trimmed.length > 0 && trimmed.length <= MESSAGE_MAX_LENGTH && !disabled;

  const submit = () => {
    if (!canSend) return;
    onSend(trimmed);
    setContent("");
  };

  return (
    <div className="flex items-start gap-2">
      <Textarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        placeholder={disabled ? t("messages.threadClosed") : t("messages.composerPlaceholder")}
        aria-label={t("messages.composerLabel")}
        maxLength={MESSAGE_MAX_LENGTH}
        disabled={disabled}
        autoFocus={autoFocus}
        rows={2}
        className="flex-1 resize-none"
      />
      <div className="flex shrink-0 flex-col items-end gap-1">
        <Button
          type="button"
          size="icon"
          aria-label={t("messages.send")}
          onClick={submit}
          disabled={!canSend}
        >
          <Send className="size-4" aria-hidden="true" />
        </Button>
        <span className="text-[10px] tabular-nums text-muted-foreground">
          {content.length}/{MESSAGE_MAX_LENGTH}
        </span>
      </div>
    </div>
  );
}
