import { Store, Package } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import type { ConversationListItem } from "@/types/messages";
import { formatDate } from "@/lib/format";

/**
 * One inbox row (M4 Task 5). Always shows the *other* participant's name +
 * shop, the related crop/product when there is one, a last-message preview,
 * the relative time, and an accessible unread indicator. Closed threads are
 * labelled so the buyer never mistakes a finished negotiation for an open one.
 */
export function ConversationListItemCard({
  conversation,
  currentUserId,
}: {
  conversation: ConversationListItem;
  currentUserId: number;
}) {
  const { t, i18n } = useTranslation();
  const other =
    conversation.buyer.id === currentUserId
      ? conversation.seller
      : conversation.buyer;

  const preview = conversation.last_message_preview ?? t("messages.noMessages");
  const related = conversation.product
    ? { name: conversation.product.name, image: conversation.product.image, icon: Package }
    : conversation.listing
      ? { name: conversation.listing.crop_name, image: conversation.listing.image, icon: Store }
      : null;
  const RelatedIcon = related?.icon ?? Store;
  const unread = conversation.unread_count > 0;

  return (
    <li>
      <Link
        to={`/marketplace/messages/${conversation.id}`}
        aria-label={t("messages.openThread", {
          name: other.name,
          preview,
        })}
        className="flex items-start gap-3 rounded-lg border bg-card p-3 transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-muted text-base font-semibold text-muted-foreground">
          {other.avatar_url ? (
            <img src={other.avatar_url} alt="" className="size-full object-cover" />
          ) : (
            other.name.charAt(0).toUpperCase()
          )}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <p className="truncate text-sm font-medium">
              {other.name}
              {other.shop_name && (
                <span className="text-muted-foreground"> · {other.shop_name}</span>
              )}
            </p>
            {conversation.last_message_at && (
              <time
                dateTime={conversation.last_message_at}
                className="shrink-0 text-xs text-muted-foreground"
              >
                {formatDate(conversation.last_message_at, i18n.language)}
              </time>
            )}
          </div>

          {related && (
            <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
              <RelatedIcon className="size-3" aria-hidden />
              <span className="truncate">{related.name}</span>
            </p>
          )}

          <p
            className={`mt-0.5 truncate text-sm ${unread ? "font-medium" : "text-muted-foreground"}`}
          >
            {preview}
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-1">
          {unread && (
            <span
              role="status"
              aria-label={t("messages.unreadCount", {
                count: conversation.unread_count,
              })}
              className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground"
            >
              {conversation.unread_count}
            </span>
          )}
          {conversation.status === "closed" && (
            <Badge variant="outline">{t("messages.closed")}</Badge>
          )}
        </div>
      </Link>
    </li>
  );
}
