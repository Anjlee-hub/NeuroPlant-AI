import { useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  Bot,
  Eraser,
  MessageCircle,
  Send,
  Volume2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { SpeakButton } from "@/components/assistant/speak-button";
import { SpeechInput } from "@/components/assistant/speech-input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StateCard } from "@/components/ui/state-card";
import { cn } from "@/lib/utils";
import { SpeechSynthesisService } from "@/services/speech-synthesis";
import { replyText, VoiceAssistantService } from "@/services/voice-assistant";
import { useAuth } from "@/stores/auth";
import type { AssistantReply } from "@/types/assistant";

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  reply?: AssistantReply;
  /** ISO timestamp — server time for restored turns, client time for new ones. */
  createdAt?: string;
  isError?: boolean;
}

/**
 * Voice AI Assistant (M3, Task 6) — a conversational chat over the rule-based
 * backend assistant: text or voice input, structured replies (message +
 * sections), an optional "voice replies" mode that reads each answer aloud in
 * its own language, suggestion chips for the common questions, typing /
 * empty / error states, and a clear-conversation control. All engine logic
 * lives on the backend (reusing treatment/soil/recovery/calendar services);
 * this page only transports queries and renders replies.
 */
export function AssistantPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [voiceOutput, setVoiceOutput] = useState(true);
  const idRef = useRef(0);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const push = (message: Omit<ChatMessage, "id">) => {
    idRef.current += 1;
    setMessages((prev) => [
      ...prev,
      {
        ...message,
        id: idRef.current,
        createdAt: message.createdAt ?? new Date().toISOString(),
      },
    ]);
  };

  // React Query keeps mutation callbacks fresh each render, so onSuccess reads
  // the current `voiceOutput` toggle at call time (no stale-closure ref needed).
  const askMutation = useMutation({
    mutationFn: ({ query, lang }: { query: string; lang: string }) =>
      VoiceAssistantService.ask(query, lang),
    onSuccess: (reply: AssistantReply) => {
      push({ role: "assistant", text: reply.message, reply });
      if (voiceOutput) VoiceAssistantService.readReply(reply);
    },
    onError: () => {
      push({ role: "assistant", text: t("assistant.errorBody"), isError: true });
    },
  });

  const send = (override?: string) => {
    const query = (override ?? input).trim();
    if (!query || askMutation.isPending) return;
    push({ role: "user", text: query });
    setInput("");
    askMutation.mutate({ query, lang: i18n.language });
  };

  const clear = () => {
    SpeechSynthesisService.cancel();
    setMessages([]);
    setInput("");
    // Best-effort server clear so a reload doesn't resurrect the chat (M3.1).
    VoiceAssistantService.clearConversation().catch(() => {
      /* offline / server error — the local view is already cleared */
    });
  };

  // Restore the persisted transcript on mount so a page reload keeps the chat
  // and follow-ups stay in context (M3.1 conversation memory).
  useEffect(() => {
    if (!user) return;
    let active = true;
    VoiceAssistantService.listConversation()
      .then(({ items }) => {
        if (!active) return;
        idRef.current = items.length;
        setMessages(
          items.map((item, index) => ({
            id: index + 1,
            role: item.role,
            text: item.content,
            createdAt: item.created_at,
            // Badges + speech locale are restored; sections aren't persisted.
            reply:
              item.role === "assistant" && item.intent && item.lang
                ? {
                    intent: item.intent,
                    message: item.content,
                    sections: [],
                    lang: item.lang,
                  }
                : undefined,
          })),
        );
      })
      .catch(() => {
        /* offline / not yet migrated — start with an empty chat */
      });
    return () => {
      active = false;
    };
  }, [user]);

  useEffect(() => {
    // Optional-call guard: scrollTo is missing in some embedded/legacy webviews.
    scrollRef.current?.scrollTo?.({ top: scrollRef.current.scrollHeight });
  }, [messages, askMutation.isPending]);

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard icon={MessageCircle} title={t("assistant.authRequired")}>
          <Button asChild>
            <Link to="/login">{t("assistant.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <MessageCircle className="size-6 text-brand-600 dark:text-brand-400" aria-hidden="true" />
            {t("nav.assistant")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("assistant.tagline")}</p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-pressed={voiceOutput}
            onClick={() => setVoiceOutput((value) => !value)}
            disabled={!VoiceAssistantService.isVoiceSupported()}
          >
            <Volume2 className="size-4" aria-hidden="true" />
            {t("assistant.voiceOutput")}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={clear}
            disabled={messages.length === 0}
          >
            <Eraser className="size-4" aria-hidden="true" />
            {t("assistant.clear")}
          </Button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className={cn(
          "flex h-[58vh] min-h-72 flex-col gap-4 overflow-y-auto rounded-lg border bg-muted/20 p-4",
          messages.length === 0 && "justify-center",
        )}
        role="log"
        aria-live="polite"
        aria-label={t("assistant.conversation")}
      >
        {messages.length === 0 && !askMutation.isPending ? (
          <EmptyState onSend={send} />
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {askMutation.isPending && <TypingIndicator />}
          </>
        )}
      </div>

      <div className="flex items-start gap-2">
        <SpeechInput
          value={input}
          onChange={setInput}
          onSubmit={() => send()}
          placeholder={t("assistant.inputPlaceholder")}
          disabled={askMutation.isPending}
          className="flex-1"
        />
        <Button
          type="button"
          size="icon"
          className="shrink-0"
          aria-label={t("assistant.send")}
          onClick={() => send()}
          disabled={!input.trim() || askMutation.isPending}
        >
          <Send className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

/** One chat bubble: user (right, filled) or assistant (left, with reply + speak). */
function MessageBubble({ message }: { message: ChatMessage }) {
  const { t } = useTranslation();

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
          {message.text}
          {message.createdAt && (
            <span
              className="mt-1 block text-right text-[10px] font-normal opacity-70"
              title={formatDate(message.createdAt)}
            >
              {formatTime(message.createdAt)}
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2">
      <Bot className="mt-1 size-5 shrink-0 text-brand-600 dark:text-brand-400" aria-hidden="true" />
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm border bg-background px-4 py-2.5">
        {message.isError ? (
          <p role="alert" className="flex items-center gap-2 text-sm font-medium text-destructive">
            <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
            {message.text}
          </p>
        ) : (
          <>
            <p className="whitespace-pre-line text-sm leading-relaxed">{message.text}</p>
            {message.reply && (
              <>
                <div className="mt-2 flex items-center gap-1.5 border-t pt-2">
                  <Badge variant="outline" className="text-[10px]">
                    {t(`assistant.intents.${message.reply.intent}`, {
                      defaultValue: message.reply.intent,
                    })}
                  </Badge>
                  <SpeakButton text={replyText(message.reply)} lang={message.reply.lang} />
                </div>
                {message.reply.sections.length > 0 && (
                  <div className="mt-2 flex flex-col gap-2.5 border-t pt-2">
                    {message.reply.sections.map((section, index) => (
                      <div key={index}>
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          {section.title}
                        </p>
                        <p className="mt-0.5 whitespace-pre-line text-sm text-muted-foreground">
                          {section.body}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
            {message.createdAt && (
              <span
                className="mt-1.5 block text-right text-[10px] text-muted-foreground/70"
                title={formatDate(message.createdAt)}
              >
                {formatTime(message.createdAt)}
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/** Time-only stamp (e.g. "14:05") for a chat bubble. */
function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/** Full readable date for the hover title of a chat bubble stamp. */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleString([], {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Empty state: greeting + tappable suggestion chips that send the question. */
function EmptyState({ onSend }: { onSend: (query: string) => void }) {
  const { t } = useTranslation();
  const suggestions = t("assistant.suggestions", {
    returnObjects: true,
  }) as string[];

  return (
    <div className="flex flex-col items-center gap-4 text-center">
      <Bot className="size-10 text-muted-foreground" aria-hidden="true" />
      <div>
        <h2 className="text-lg font-semibold">{t("assistant.emptyTitle")}</h2>
        <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
          {t("assistant.emptyBody")}
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2" aria-label={t("assistant.suggestionsLabel")}>
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onSend(suggestion)}
            className="rounded-full border bg-background px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Accessible three-dot "assistant is typing" indicator. */
function TypingIndicator() {
  const { t } = useTranslation();
  return (
    <div role="status" aria-label={t("assistant.typing")} className="flex items-center gap-1.5">
      <span className="flex gap-1">
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.3s]" />
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.15s]" />
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/60" />
      </span>
      <span className="sr-only">{t("assistant.typing")}</span>
    </div>
  );
}
