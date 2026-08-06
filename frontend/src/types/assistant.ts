/**
 * Voice AI assistant domain types — mirrors the backend `AssistantReplyOut`
 * shape for `POST /assistant` (see `backend/app/schemas/assistant.py`). The
 * service routes a free-text query (English or Hindi) to the existing engines
 * and returns a localized, speakable reply: the conversational `message`
 * plus optional `sections` the UI can render as cards and/or read aloud.
 */

export type AssistantIntent =
  | "greeting"
  | "help"
  | "disease"
  | "treatment"
  | "fertilizer"
  | "soil"
  | "calendar"
  | "recovery"
  | "fallback";

export interface AssistantSection {
  title: string;
  body: string;
}

export interface AssistantReply {
  intent: AssistantIntent;
  message: string;
  sections: AssistantSection[];
  lang: string;
}

export interface AssistantRequest {
  query: string;
  lang?: string;
}
