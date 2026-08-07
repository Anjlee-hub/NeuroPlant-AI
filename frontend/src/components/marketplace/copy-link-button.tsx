import { Check, Link2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";

/**
 * Copy a listing's URL to the clipboard (M4 Task 3). Uses the async Clipboard
 * API where available and a legacy execCommand fallback in non-secure contexts
 * (or jsdom test runs) so the action never silently dies. Shows a brief
 * "Link copied" confirmation and reverts after 2s.
 */
export function CopyLinkButton({ url }: { url: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    },
    [],
  );

  const copy = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = url;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }
    } catch {
      return; // Clipboard blocked — nothing sensible to do, stay quiet.
    }
    setCopied(true);
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button
      variant="outline"
      size="sm"
      aria-live="polite"
      onClick={() => void copy()}
    >
      {copied ? (
        <Check className="size-4" aria-hidden />
      ) : (
        <Link2 className="size-4" aria-hidden />
      )}
      {copied
        ? t("marketplaceBuy.actions.linkCopied")
        : t("marketplaceBuy.actions.copyLink")}
    </Button>
  );
}
