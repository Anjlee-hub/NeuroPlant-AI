import { useQuery } from "@tanstack/react-query";
import { MessageCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ConversationList } from "@/components/messages/conversation-list";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api } from "@/lib/api";
import { useAuth } from "@/stores/auth";

export const CONVERSATIONS_KEY = ["conversations"] as const;

/**
 * Inbox (M4 Task 5) — every thread the caller is a participant of, newest
 * activity first, with unread counts and last-message previews. Auth-gated;
 * loading shows skeletons, failures offer a retry, and an empty inbox has a
 * gentle call-to-action back to the marketplace.
 */
export function MessagesListPage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const conversationsQuery = useQuery({
    queryKey: CONVERSATIONS_KEY,
    queryFn: () => api.listConversations(),
    enabled: !!user,
  });

  if (!user) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <StateCard icon={MessageCircle} title={t("messages.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("messages.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight sm:text-3xl">
          <MessageCircle className="size-7 text-brand-600 dark:text-brand-400" aria-hidden />
          {t("messages.title")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("messages.subtitle")}</p>
      </header>

      <div className="mt-6">
        {conversationsQuery.isPending ? (
          <div role="status" aria-label={t("messages.loading")} className="flex flex-col gap-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : conversationsQuery.isError ? (
          <StateCard
            icon={MessageCircle}
            title={t("messages.errorTitle")}
            body={t("messages.errorBody")}
            tone="destructive"
          >
            <Button variant="outline" onClick={() => void conversationsQuery.refetch()}>
              {t("common.retry")}
            </Button>
          </StateCard>
        ) : conversationsQuery.data.length === 0 ? (
          <StateCard icon={MessageCircle} title={t("messages.emptyTitle")} body={t("messages.emptyBody")}>
            <Button asChild variant="outline">
              <Link to="/marketplace/browse">{t("messages.browseMarketplace")}</Link>
            </Button>
          </StateCard>
        ) : (
          <ConversationList
            conversations={conversationsQuery.data}
            currentUserId={user.id}
          />
        )}
      </div>
    </div>
  );
}
