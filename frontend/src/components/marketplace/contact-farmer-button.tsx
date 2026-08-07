import { MessageCircle } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";

/**
 * Placeholder for buyer→farmer messaging (M4 Task 5) — deliberately NOT a chat
 * UI. Clicking toggles a short "coming soon" note so the intended entry point
 * is discoverable and testable, and the component is already shaped for the
 * future task (a farmer id the message thread will need).
 */
export function ContactFarmerButton({ farmerId }: { farmerId: number }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        size="sm"
        aria-expanded={open}
        data-farmer-id={farmerId}
        onClick={() => setOpen((value) => !value)}
      >
        <MessageCircle className="size-4" aria-hidden />
        {t("marketplaceBuy.actions.contactFarmer")}
      </Button>
      {open && (
        <p role="status" className="text-sm text-muted-foreground">
          {t("marketplaceBuy.actions.contactSoon")}
        </p>
      )}
    </div>
  );
}
