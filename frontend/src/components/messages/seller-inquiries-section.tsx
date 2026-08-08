import { useQuery } from "@tanstack/react-query";
import { Inbox } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ConversationList } from "@/components/messages/conversation-list";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { CONVERSATIONS_KEY } from "@/pages/messages-list";

/**
 * Seller-portal inquiries (M4 Task 5) — a compact inbox on /marketplace/shop
 * showing only threads where the current user is the seller side. Each row
 * links into the full thread (reply, mark-read, close all live there). Unread
 * totals surface at a glance; a red-on-grey inline error offers a retry.
 */
export function SellerInquiriesSection({ currentUserId }: { currentUserId: number }) {
  const { t } = useTranslation();

  const conversationsQuery = useQuery({
    queryKey: CONVERSATIONS_KEY,
    queryFn: () => api.listConversations(),
  });

  const asSeller = (conversationsQuery.data ?? []).filter(
    (conversation) => conversation.seller.id === currentUserId,
  );
  const unreadTotal = asSeller.reduce((sum, row) => sum + row.unread_count, 0);

  return (
    <section aria-labelledby="inquiries-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="inquiries-heading" className="flex items-center gap-2 text-lg font-semibold">
          <Inbox className="size-5 text-muted-foreground" aria-hidden />
          {t("messages.inquiriesTitle")}
        </h2>
        {unreadTotal > 0 && (
          <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
            {t("messages.inquiriesUnread", { count: unreadTotal })}
          </span>
        )}
      </div>

      <div className="mt-3">
        {conversationsQuery.isPending ? (
          <div role="status" aria-label={t("messages.loading")} className="flex flex-col gap-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : conversationsQuery.isError ? (
          <StateCard icon={Inbox} title={t("messages.errorTitle")} body={t("messages.errorBody")} tone="destructive">
            <Button variant="outline" onClick={() => void conversationsQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : asSeller.length === 0 ? (
          <p className="rounded-md border bg-muted/40 p-6 text-center text-sm text-muted-foreground">
            {t("messages.inquiriesEmpty")}
          </p>
        ) : (
          <ConversationList conversations={asSeller} currentUserId={currentUserId} />
        )}
      </div>

      {asSeller.length > 0 && (
        <p className="mt-3">
          <Button asChild variant="link" size="sm">
            <Link to="/marketplace/messages">{t("messages.viewAll")}</Link>
          </Button>
        </p>
      )}
    </section>
  );
}
