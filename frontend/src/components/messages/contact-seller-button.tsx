import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageCircle } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { CONVERSATIONS_KEY } from "@/pages/messages-list";
import { api, errorMessage } from "@/lib/api";

/**
 * Real "Contact Seller / Contact Farmer" action (M4 Task 5). Clicking starts —
 * or reuses — the conversation for the given context (a crop listing, a
 * product, or an explicit seller id) and opens it in the messaging UI. The
 * backend dedupes, so a second click on the same item never stacks a new
 * thread. Honest states: a loading label while the thread is created, and an
 * inline error if the request fails.
 */
export function ContactSellerButton({
  label,
  listingId,
  productId,
  sellerId,
}: {
  label: string;
  listingId?: number;
  productId?: number;
  sellerId?: number;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api.createConversation({
        listing_id: listingId,
        product_id: productId,
        seller_id: sellerId,
      }),
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: CONVERSATIONS_KEY });
      navigate(`/marketplace/messages/${conversation.id}`);
    },
    onError: (err) => setError(errorMessage(err)),
  });

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        size="sm"
        aria-busy={create.isPending}
        disabled={create.isPending}
        onClick={() => {
          setError(null);
          create.mutate();
        }}
      >
        <MessageCircle className="size-4" aria-hidden />
        {create.isPending ? t("messages.opening") : label}
      </Button>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
