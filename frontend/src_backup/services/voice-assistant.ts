/**
 * Voice assistant orchestration service (M3, Task 6) — the single seam the UI
 * talks to for voice-first conversations. It composes the two framework-free
 * speech services (recognition → synthesis) with the assistant backend:
 * send a query, get a structured reply, and optionally read it aloud in the
 * reply's own language. UI components reuse this service so recognition /
 * synthesis wiring is never duplicated across surfaces.
 *
 * `speechLocale` maps the app's language codes to the BCP-47 voice locales the
 * Web Speech APIs expect. It grows with the i18n registry (M4 adds more Indian
 * languages — one row per code here).
 */

import { api } from "@/lib/api";
import type {
  AssistantReply,
  AssistantRequest,
  ConversationHistory,
} from "@/types/assistant";
import { SpeechRecognitionService } from "@/services/speech-recognition";
import {
  SpeechSynthesisService,
  type SpeechSynthesisHandlers,
} from "@/services/speech-synthesis";

/** App language code → BCP-47 voice locale (Indian voices by default). */
const SPEECH_LOCALES: Record<string, string> = {
  en: "en-IN",
  hi: "hi-IN",
};

/** Resolve an app language code to a BCP-47 voice locale. */
export function speechLocale(lang: string): string {
  return SPEECH_LOCALES[lang] ?? lang;
}

/** Combine a reply into one speakable string: message first, then each section. */
export function replyText(reply: AssistantReply): string {
  return [reply.message, ...reply.sections.map((s) => `${s.title}. ${s.body}`)]
    .filter((part) => part.trim().length > 0)
    .join(". ");
}

export class VoiceAssistantService {
  /** Send a free-text query to the assistant backend (English or Hindi). */
  static ask(query: string, lang: string): Promise<AssistantReply> {
    const payload: AssistantRequest = { query, lang };
    return api.askAssistant(payload);
  }

  /** Restore the user's chat transcript, oldest first (page-load restore). */
  static listConversation(): Promise<ConversationHistory> {
    return api.getAssistantConversation();
  }

  /** Clear the user's entire chat transcript (clear-chat). */
  static clearConversation(): Promise<void> {
    return api.clearAssistantConversation();
  }

  /** Read a reply aloud in its own language: message first, then each section. */
  static readReply(reply: AssistantReply, handlers?: SpeechSynthesisHandlers): void {
    SpeechSynthesisService.speak(replyText(reply), speechLocale(reply.lang), handlers);
  }

  /** True when this browser can do voice input, voice output, or both. */
  static isVoiceSupported(): boolean {
    return SpeechRecognitionService.isSupported() || SpeechSynthesisService.isSupported();
  }
}
