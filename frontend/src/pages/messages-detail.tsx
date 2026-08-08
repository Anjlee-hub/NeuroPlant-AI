import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Lock, MessageCircle, Store } from "lucide-react";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { MessageBubble } from "@/components/messages/message-bubble";
import { MessageComposer } from "@/components/messages/message-composer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StateCard } from "@/components/ui/state-card";
import { api, errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useAuth } from "@/stores/auth";
import type { ConversationDetail } from "@/types/messages";

export const CONVERSATION_KEY = ["conversation"] as const;

/**
 * One thread (M4 Task 5). History (own messages right, other side left), a
 * composer that sends on Enter, an auto mark-read on open, and a close control
 * for the caller. Honest states throughout: skeletons while loading, an inline
 * error + retry on failure, a 404/not-participant card, and a locked composer
 * with an explanation once the thread is closed.
 */
export function MessagesDetailPage() {
  const { t, i18n } = useTranslation();
  const { conversationId } = useParams<{ conversationId: string }>();
  const id = Number(conversationId);
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const conversationQuery = useQuery({
    queryKey: CONVERSATION_KEY,
    queryFn: () => api.getConversation(id),
    enabled: !!user && Number.isFinite(id),
  });

  const sendMutation = useMutation({
    mutationFn: (content: string) => api.sendMessage(id, { content }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CONVERSATION_KEY }),
  });

  const closeMutation = useMutation({
    mutationFn: () => api.closeConversation(id),
    onSuccess: (updated) => {
      queryClient.setQueryData<ConversationDetail>(CONVERSATION_KEY, (old) =>
        old ? { ...old, status: updated.status } : old,
      );
    },
  });

  // Mark the other side's messages as read once, when we open a thread with
  // unread. Refires on refetch while unread > 0, which is the desired nudge.
  const unreadCount = conversationQuery.data?.unread_count;
  useEffect(() => {
    if (!unreadCount) return;
    api.markConversationRead(id).catch(() => {
      /* best-effort; the next open refetches */
    });
  }, [unreadCount, id]);

  // Keep the newest message in view after sends/loads.
  useEffect(() => {
    scrollRef.current?.scrollTo?.({ top: scrollRef.current.scrollHeight });
  }, [conversationQuery.data?.messages.length, sendMutation.isPending]);

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

  if (Number.isNaN(id)) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <StateCard icon={MessageCircle} title={t("messages.notFoundTitle")} body={t("messages.notFoundBody")}>
          <Button asChild variant="outline">
            <Link to="/marketplace/messages">{t("messages.backToInbox")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  const conversation = conversationQuery.data;
  const other = conversation
    ? conversation.buyer.id === user.id
      ? conversation.seller
      : conversation.buyer
    : null;
  // A 404 means the thread doesn't exist or isn't the caller's (enumeration
  // guard) — retrying can't change that. Anything else is a transient failure.
  const notFound =
    (conversationQuery.error as { status?: number } | null)?.status === 404;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <nav aria-label={t("nav.messages")}>
        <Button asChild variant="ghost" size="sm">
          <Link to="/marketplace/messages">
            <ArrowLeft className="size-4" aria-hidden />
            {t("messages.backToInbox")}
          </Link>
        </Button>
      </nav>

      {conversationQuery.isPending ? (
        <div role="status" aria-label={t("messages.loading")} className="mt-4 flex flex-col gap-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      ) : conversationQuery.isError ? (
        <div className="mt-4">
          {notFound ? (
            <StateCard
              icon={MessageCircle}
              title={t("messages.notFoundTitle")}
              body={t("messages.notFoundBody")}
            >
              <Button asChild variant="outline">
                <Link to="/marketplace/messages">{t("messages.backToInbox")}</Link>
              </Button>
            </StateCard>
          ) : (
            <StateCard
              icon={MessageCircle}
              title={t("messages.threadErrorTitle")}
              body={t("messages.threadErrorBody")}
              tone="destructive"
            >
              <Button variant="outline" onClick={() => void conversationQuery.refetch()}>
                {t("common.retry")}
              </Button>
            </StateCard>
          )}
        </div>
      ) : conversation && other ? (
        <div className="mt-4 overflow-hidden rounded-lg border bg-card">
          <header className="flex flex-wrap items-start justify-between gap-2 border-b p-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="flex items-center gap-2 text-lg font-semibold">
                  <span className="flex size-8 items-center justify-center overflow-hidden rounded-full bg-muted text-sm font-semibold text-muted-foreground">
                    {other.avatar_url ? (
                      <img src={other.avatar_url} alt="" className="size-full object-cover" />
                    ) : (
                      other.name.charAt(0).toUpperCase()
                    )}
                  </span>
                  <span className="truncate">{other.name}</span>
                </h1>
                {conversation.status === "closed" && <Badge variant="outline">{t("messages.closed")}</Badge>}
              </div>
              <p className="mt-1 flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
                {other.shop_name && (
                  <>
                    <Store className="size-3.5" aria-hidden />
                    <span>{other.shop_name}</span>
                  </>
                )}
                {conversation.product && <span>· {conversation.product.name}</span>}
                {conversation.listing && <span>· {conversation.listing.crop_name}</span>}
                {conversation.created_at && (
                  <time dateTime={conversation.created_at} className="text-xs">
                    · {formatDate(conversation.created_at, i18n.language)}
                  </time>
                )}
              </p>
            </div>
            {conversation.status === "active" && (
              <Button
                variant="outline"
                size="sm"
                disabled={closeMutation.isPending}
                aria-busy={closeMutation.isPending}
                onClick={() => {
                  const ok = window.confirm(t("messages.confirmClose"));
                  if (ok) closeMutation.mutate();
                }}
              >
                {t("messages.closeThread")}
              </Button>
            )}
          </header>

          <div
            ref={scrollRef}
            role="log"
            aria-live="polite"
            aria-label={t("messages.threadLabel")}
            className="flex max-h-[55vh] min-h-64 flex-col gap-3 overflow-y-auto bg-muted/20 p-4"
          >
            {conversation.messages.length === 0 ? (
              <p className="m-auto text-sm text-muted-foreground">{t("messages.noMessages")}</p>
            ) : (
              conversation.messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isOwn={message.sender_id === user.id}
                />
              ))
            )}
            {sendMutation.isPending && (
              <p className="text-sm text-muted-foreground">{t("messages.sending")}</p>
            )}
          </div>

          <footer className="border-t p-4">
            {conversation.status === "closed" ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Lock className="size-4" aria-hidden />
                {t("messages.threadClosedNote")}
              </p>
            ) : (
              <MessageComposer
                disabled={sendMutation.isPending}
                onSend={(content) => sendMutation.mutate(content)}
                autoFocus
              />
            )}
            {sendMutation.isError && (
              <p role="alert" className="mt-2 text-sm text-destructive">
                {errorMessage(sendMutation.error)}
              </p>
            )}
          </footer>
        </div>
      ) : null}
    </div>
  );
}
