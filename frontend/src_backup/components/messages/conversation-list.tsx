import { useTranslation } from "react-i18next";

import { ConversationListItemCard } from "@/components/messages/conversation-list-item";
import type { ConversationListItem } from "@/types/messages";

/** Ordered inbox list — one card per thread (M4 Task 5). */
export function ConversationList({
  conversations,
  currentUserId,
}: {
  conversations: ConversationListItem[];
  currentUserId: number;
}) {
  const { t } = useTranslation();

  return (
    <ul aria-label={t("messages.inboxLabel")} className="flex flex-col gap-2">
      {conversations.map((conversation) => (
        <ConversationListItemCard
          key={conversation.id}
          conversation={conversation}
          currentUserId={currentUserId}
        />
      ))}
    </ul>
  );
}
