/**
 * AI assistant domain types — mirrors the backend `assistant.py` schemas
 * (`AssistantReplyOut`, `ConversationMessageOut`). The service routes a
 * free-text query (English or Hindi) to the existing engines and returns a
 * localized, speakable reply: the conversational `message` plus optional
 * `sections` the UI can render as cards and/or read aloud.
 *
 * M3.1 extends the intent union to the full conversational set (identity,
 * thanks, smalltalk, disease_explain, symptoms, watering, neem,
 * recovery_timeline, report, non_agriculture, conversation) and adds the
 * persisted transcript types backing `GET/DELETE /assistant/conversation`.
 */

export type AssistantIntent =
  // Social / static
  | "greeting"
  | "identity"
  | "help"
  | "thanks"
  | "smalltalk"
  // Data-backed (reuse the engine services)
  | "disease"
  | "disease_explain"
  | "symptoms"
  | "treatment"
  | "fertilizer"
  | "watering"
  | "neem"
  | "soil"
  | "recovery"
  | "recovery_timeline"
  | "calendar"
  // Conversational plumbing
  | "report"
  | "conversation"
  // Boundary
  | "non_agriculture";

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

/** One persisted turn of the user's chat (for history restore). */
export interface ConversationMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  intent: AssistantIntent | null;
  lang: string | null;
  created_at: string;
}

/** The user's recent transcript, oldest first. */
export interface ConversationHistory {
  items: ConversationMessage[];
}
