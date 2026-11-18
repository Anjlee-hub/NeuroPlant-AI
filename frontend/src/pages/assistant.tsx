
import { useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowDown,
  Bot,
  Check,
  Eraser,
  Leaf,
  MessageCircle,
  Mic,
  Send,
  ShieldCheck,
  Sparkles,
  Sprout,
  Volume2,
  Wifi,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
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
  createdAt?: string;
  isError?: boolean;
}

const suggestions = [
  {
    icon: Leaf,
    key: 0,
    color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  },
  {
    icon: ShieldCheck,
    key: 1,
    color: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  },
  {
    icon: Sprout,
    key: 2,
    color: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
  },
  {
    icon: MessageCircle,
    key: 3,
    color: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  },
];

export function AssistantPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [voiceOutput, setVoiceOutput] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);

  const idRef = useRef(0);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const push = (message: Omit<ChatMessage, "id">) => {
    idRef.current += 1;

    setMessages((previous) => [
      ...previous,
      {
        ...message,
        id: idRef.current,
        createdAt: message.createdAt ?? new Date().toISOString(),
      },
    ]);
  };

  const askMutation = useMutation({
    mutationFn: ({ query, lang }: { query: string; lang: string }) =>
      VoiceAssistantService.ask(query, lang),

    onSuccess: (reply: AssistantReply) => {
      push({
        role: "assistant",
        text: reply.message,
        reply,
      });

      if (voiceOutput) {
        VoiceAssistantService.readReply(reply);
      }
    },

    onError: () => {
      push({
        role: "assistant",
        text: t("assistant.errorBody"),
        isError: true,
      });
    },
  });

  const send = (override?: string) => {
    const query = (override ?? input).trim();

    if (!query || askMutation.isPending) return;

    SpeechSynthesisService.cancel();

    push({
      role: "user",
      text: query,
    });

    setInput("");

    askMutation.mutate({
      query,
      lang: i18n.language,
    });
  };

  const clear = () => {
    SpeechSynthesisService.cancel();
    setMessages([]);
    setInput("");
    idRef.current = 0;

    VoiceAssistantService.clearConversation().catch(() => {
      // The local conversation is already cleared.
    });
  };

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
        // Offline or unavailable history: start with an empty conversation.
      });

    return () => {
      active = false;
    };
  }, [user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, askMutation.isPending]);

  const handleScroll = () => {
    const element = scrollRef.current;
    if (!element) return;

    const distance =
      element.scrollHeight - element.scrollTop - element.clientHeight;

    setShowScrollButton(distance > 180);
  };

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  };

  if (!user) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <StateCard
          icon={MessageCircle}
          title={t("assistant.authRequired")}
        >
          <Button asChild>
            <Link to="/login">{t("assistant.signIn")}</Link>
          </Button>
        </StateCard>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-gradient-to-b from-emerald-50/70 via-background to-background dark:from-emerald-950/20">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-3 py-5 sm:px-6 sm:py-8">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex flex-col justify-between gap-4 rounded-2xl border border-emerald-100 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-emerald-900/50 dark:bg-card/80 sm:flex-row sm:items-center sm:p-6"
        >
          <div className="flex items-center gap-4">
            <div className="relative flex size-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-green-800 text-white shadow-lg shadow-emerald-900/15">
              <Bot className="size-8" />
              <span className="absolute -bottom-1 -right-1 flex size-4 items-center justify-center rounded-full border-2 border-white bg-green-400 dark:border-card">
                <span className="size-1.5 rounded-full bg-white" />
              </span>
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight sm:text-2xl">
                  {t("nav.assistant")}
                </h1>
                <Badge variant="success" className="gap-1">
                  <Sparkles className="size-3" />
                  AI Assistant
                </Badge>
              </div>

              <p className="mt-1 text-sm text-muted-foreground">
                {t("assistant.tagline")}
              </p>

              <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-green-500" />
                  Ready to help
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Wifi className="size-3.5" />
                  Connected to your farming assistant
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant={voiceOutput ? "secondary" : "outline"}
              size="sm"
              aria-pressed={voiceOutput}
              onClick={() => {
                setVoiceOutput((value) => !value);
                if (voiceOutput) SpeechSynthesisService.cancel();
              }}
              disabled={!VoiceAssistantService.isVoiceSupported()}
              className="gap-2"
            >
              <Volume2 className="size-4" />
              {t("assistant.voiceOutput")}
              {voiceOutput && <Check className="size-3.5" />}
            </Button>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={clear}
              disabled={messages.length === 0}
              className="gap-2"
            >
              <Eraser className="size-4" />
              {t("assistant.clear")}
            </Button>
          </div>
        </motion.header>

        {/* Main chat panel */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.08 }}
          className="relative flex min-h-[68vh] flex-col overflow-hidden rounded-2xl border bg-card shadow-sm"
        >
          {/* Chat panel top bar */}
          <div className="flex items-center justify-between border-b bg-muted/20 px-4 py-3 sm:px-6">
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">
                <Sprout className="size-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">NeuroPlant Assistant</p>
                <p className="text-xs text-muted-foreground">
                  Your crop-care companion
                </p>
              </div>
            </div>

            <Badge variant="outline" className="gap-1.5 font-normal">
              <span className="size-1.5 rounded-full bg-green-500" />
              {t("assistant.conversation")}
            </Badge>
          </div>

          {/* Conversation */}
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className={cn(
              "relative flex flex-1 flex-col gap-5 overflow-y-auto bg-gradient-to-b from-muted/10 to-background px-3 py-5 sm:px-6 sm:py-7",
              messages.length === 0 && !askMutation.isPending
                ? "justify-center"
                : "min-h-[420px]",
            )}
            role="log"
            aria-live="polite"
            aria-label={t("assistant.conversation")}
          >
            {messages.length === 0 && !askMutation.isPending ? (
              <EmptyState onSend={send} />
            ) : (
              <AnimatePresence initial={false}>
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                  />
                ))}

                {askMutation.isPending && <TypingIndicator key="typing" />}
              </AnimatePresence>
            )}

            <div ref={bottomRef} />

            <AnimatePresence>
              {showScrollButton && (
                <motion.button
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  type="button"
                  onClick={scrollToBottom}
                  aria-label="Scroll to latest message"
                  className="sticky bottom-2 left-full flex size-10 shrink-0 items-center justify-center rounded-full border bg-background text-foreground shadow-lg transition-colors hover:bg-accent"
                >
                  <ArrowDown className="size-4" />
                </motion.button>
              )}
            </AnimatePresence>
          </div>

          {/* Input area */}
          <div className="border-t bg-background p-3 sm:p-5">
            <div className="mx-auto max-w-4xl">
              <div className="rounded-2xl border bg-muted/20 p-2 shadow-sm transition-all focus-within:border-emerald-500/60 focus-within:ring-2 focus-within:ring-emerald-500/10">
                <div className="flex items-center gap-2">
                  <SpeechInput
                    value={input}
                    onChange={setInput}
                    onSubmit={() => send()}
                    placeholder={t("assistant.inputPlaceholder")}
                    disabled={askMutation.isPending}
                    className="min-w-0 flex-1"
                  />

                  <Button
                    type="button"
                    size="icon"
                    className="size-10 shrink-0 rounded-xl bg-emerald-700 text-white hover:bg-emerald-800 dark:bg-emerald-600 dark:hover:bg-emerald-700"
                    aria-label={t("assistant.send")}
                    onClick={() => send()}
                    disabled={!input.trim() || askMutation.isPending}
                  >
                    <Send className="size-4" />
                  </Button>
                </div>
              </div>

              <p className="mt-2 text-center text-[11px] text-muted-foreground">
                <ShieldCheck className="mr-1 inline size-3" />
                Ask questions about crop diseases, treatment, soil care and
                farming tasks.
              </p>
            </div>
          </div>
        </motion.section>

        <p className="pb-2 text-center text-xs text-muted-foreground">
          NeuroPlant AI · Intelligent crop-care assistance
        </p>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const { t } = useTranslation();

  if (message.role === "user") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12, x: 8 }}
        animate={{ opacity: 1, y: 0, x: 0 }}
        exit={{ opacity: 0, y: -5 }}
        transition={{ duration: 0.25 }}
        className="flex justify-end"
      >
        <div className="max-w-[88%] rounded-2xl rounded-br-md bg-emerald-800 px-4 py-3 text-sm leading-relaxed text-white shadow-sm dark:bg-emerald-700 sm:max-w-[75%]">
          <p className="whitespace-pre-wrap">{message.text}</p>

          {message.createdAt && (
            <span
              className="mt-1.5 block text-right text-[10px] text-white/65"
              title={formatDate(message.createdAt)}
            >
              {formatTime(message.createdAt)}
            </span>
          )}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, x: -8 }}
      animate={{ opacity: 1, y: 0, x: 0 }}
      exit={{ opacity: 0, y: -5 }}
      transition={{ duration: 0.28 }}
      className="flex items-start gap-2.5 sm:gap-3"
    >
      <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-green-800 text-white shadow-sm">
        <Bot className="size-5" />
      </div>

      <div className="max-w-[88%] min-w-0 rounded-2xl rounded-tl-md border bg-background px-4 py-3 shadow-sm sm:max-w-[75%]">
        {message.isError ? (
          <div
            role="alert"
            className="flex items-start gap-2 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <p>{message.text}</p>
          </div>
        ) : (
          <>
            <p className="whitespace-pre-line text-sm leading-7">
              {message.text}
            </p>

            {message.reply && (
              <>
                <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-2">
                  <Badge variant="outline" className="text-[10px]">
                    {t(`assistant.intents.${message.reply.intent}`, {
                      defaultValue: message.reply.intent,
                    })}
                  </Badge>

                  <SpeakButton
                    text={replyText(message.reply)}
                    lang={message.reply.lang}
                    className="size-8"
                  />
                </div>

                {message.reply.sections.length > 0 && (
                  <div className="mt-3 flex flex-col gap-3 border-t pt-3">
                    {message.reply.sections.map((section, index) => (
                      <div
                        key={`${section.title}-${index}`}
                        className="rounded-xl bg-muted/40 p-3"
                      >
                        <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
                          {section.title}
                        </p>
                        <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
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
                className="mt-2 block text-right text-[10px] text-muted-foreground/70"
                title={formatDate(message.createdAt)}
              >
                {formatTime(message.createdAt)}
              </span>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}

function EmptyState({ onSend }: { onSend: (query: string) => void }) {
  const { t } = useTranslation();

  const translatedSuggestions = t("assistant.suggestions", {
    returnObjects: true,
  }) as string[];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mx-auto flex w-full max-w-2xl flex-col items-center gap-6 py-5 text-center"
    >
      <div className="relative flex size-20 items-center justify-center rounded-3xl bg-gradient-to-br from-emerald-100 to-green-200 text-emerald-800 shadow-inner dark:from-emerald-900/60 dark:to-green-950 dark:text-emerald-300">
        <Bot className="size-11" />
        <motion.span
          animate={{ y: [0, -5, 0], rotate: [0, 5, 0] }}
          transition={{ duration: 2.5, repeat: Infinity }}
          className="absolute -right-2 -top-2 flex size-8 items-center justify-center rounded-xl bg-white text-amber-500 shadow-md dark:bg-card"
        >
          <Sparkles className="size-4" />
        </motion.span>
      </div>

      <div className="max-w-lg">
        <h2 className="text-xl font-bold tracking-tight sm:text-2xl">
          {t("assistant.emptyTitle")}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {t("assistant.emptyBody")}
        </p>
      </div>

      <div className="w-full">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("assistant.suggestionsLabel")}
        </p>

        <div className="grid gap-2 sm:grid-cols-2">
          {translatedSuggestions.map((suggestion, index) => {
            const item = suggestions[index] ?? suggestions[0];
            const Icon = item.icon;

            return (
              <motion.button
                key={suggestion}
                type="button"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.07 }}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => onSend(suggestion)}
                className="group flex min-h-16 items-center gap-3 rounded-xl border bg-background p-3 text-left transition-colors hover:border-emerald-300 hover:bg-emerald-50/70 dark:hover:border-emerald-800 dark:hover:bg-emerald-950/30"
              >
                <span
                  className={cn(
                    "flex size-10 shrink-0 items-center justify-center rounded-xl",
                    item.color,
                  )}
                >
                  <Icon className="size-5" />
                </span>

                <span className="min-w-0 flex-1 text-sm font-medium leading-snug text-foreground">
                  {suggestion}
                </span>

                <Send className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-emerald-700 dark:group-hover:text-emerald-300" />
              </motion.button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Mic className="size-3.5" />
          Voice input
        </span>
        <span className="size-1 rounded-full bg-muted-foreground/40" />
        <span className="inline-flex items-center gap-1">
          <Volume2 className="size-3.5" />
          Spoken replies
        </span>
        <span className="size-1 rounded-full bg-muted-foreground/40" />
        <span>English and Hindi</span>
      </div>
    </motion.div>
  );
}

function TypingIndicator() {
  const { t } = useTranslation();

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex items-start gap-2.5 sm:gap-3"
    >
      <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-green-800 text-white">
        <Bot className="size-5" />
      </div>

      <div
        role="status"
        aria-label={t("assistant.typing")}
        className="flex items-center gap-3 rounded-2xl rounded-tl-md border bg-background px-4 py-3 shadow-sm"
      >
        <span className="flex items-center gap-1">
          {[0, 1, 2].map((dot) => (
            <motion.span
              key={dot}
              animate={{ y: [0, -5, 0], opacity: [0.45, 1, 0.45] }}
              transition={{
                duration: 0.7,
                repeat: Infinity,
                delay: dot * 0.15,
              }}
              className="size-2 rounded-full bg-emerald-600"
            />
          ))}
        </span>

        <span className="text-xs text-muted-foreground">
          {t("assistant.typing")}
        </span>
      </div>
    </motion.div>
  );
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString([], {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
