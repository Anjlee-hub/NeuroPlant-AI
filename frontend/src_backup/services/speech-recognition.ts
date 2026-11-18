/**
 * Speech-to-text service (M3, Task 6) — a thin, UI-free wrapper over the
 * browser's Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`).
 * It resolves the correct constructor, wires the event surface into plain
 * handlers, and accumulates final + interim transcripts so callers (the
 * SpeechInput component) never touch the browser API directly. When the API is
 * missing (jsdom, older browsers) `isSupported()` is false and the UI shows a
 * disabled mic rather than a broken one.
 *
 * This module is deliberately framework-free: tests exercise it against
 * stubbed globals and any UI (React today, others later) can reuse it. Error
 * *codes* (not sentences) are surfaced so the UI layer localizes them.
 */

/** Stable, minimal shape of the browser `SpeechRecognition` instance. */
export interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onresult: ((event: SpeechRecognitionResultEventLike) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

interface SpeechRecognitionAlternative {
  transcript: string;
}

interface SpeechRecognitionResultItem {
  readonly isFinal: boolean;
  readonly [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionResultEventLike {
  readonly resultIndex: number;
  readonly length: number;
  readonly [index: number]: SpeechRecognitionResultItem;
}

interface WindowWithSpeech {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
}

/** Normalized, localizable recognition error codes. */
export type SpeechRecognitionErrorCode =
  | "not-allowed"
  | "no-speech"
  | "audio-capture"
  | "network"
  | "aborted"
  | "unknown";

export function normalizeRecognitionError(code: string | undefined): SpeechRecognitionErrorCode {
  if (code === "not-allowed" || code === "service-not-allowed") return "not-allowed";
  if (code === "no-speech") return "no-speech";
  if (code === "audio-capture") return "audio-capture";
  if (code === "network") return "network";
  if (code === "aborted") return "aborted";
  return "unknown";
}

export interface SpeechRecognitionHandlers {
  /** The recognizer started listening. */
  onStart?: () => void;
  /** Live partial transcript (committed + interim), for instant feedback. */
  onInterim?: (text: string) => void;
  /** A final committed phrase (recognition ended with a real result). */
  onFinal?: (text: string) => void;
  /** Recognition ended (naturally, or via stop()/abort()). */
  onEnd?: () => void;
  /** A normalized, localizable error code. */
  onError?: (code: SpeechRecognitionErrorCode) => void;
}

export interface SpeechRecognitionHandle {
  start(): void;
  stop(): void;
  abort(): void;
  isListening(): boolean;
}

export class SpeechRecognitionService {
  /** True when this browser ships the Web Speech recognition API. */
  static isSupported(): boolean {
    if (typeof window === "undefined") return false;
    const w = window as WindowWithSpeech;
    return Boolean(w.SpeechRecognition || w.webkitSpeechRecognition);
  }

  /**
   * Build a live recognition session. `lang` is a BCP-47 voice locale
   * (e.g. "en-IN" / "hi-IN"). Returns a handle so the caller controls the
   * session lifecycle without touching the browser API.
   */
  static create(
    lang: string,
    handlers: SpeechRecognitionHandlers = {},
  ): SpeechRecognitionHandle {
    const ctor = SpeechRecognitionService.resolve();
    if (!ctor) {
      throw new Error("Speech recognition is not supported in this browser");
    }

    const recognition = new ctor();
    recognition.lang = lang;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    let listening = false;
    let committed = "";

    recognition.onstart = () => {
      listening = true;
      handlers.onStart?.();
    };

    recognition.onend = () => {
      listening = false;
      const final = committed.trim();
      if (final) handlers.onFinal?.(final);
      handlers.onEnd?.();
    };

    recognition.onerror = (event) => {
      listening = false;
      handlers.onError?.(normalizeRecognitionError(event.error));
    };

    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.length; i++) {
        const result = event[i];
        if (result.isFinal) {
          committed = `${committed} ${result[0].transcript}`.trim();
        } else {
          interim += result[0].transcript;
        }
      }
      // Browser fragments often carry leading whitespace → collapse runs so the
      // live transcript never shows doubled spaces between committed + interim.
      const current = (interim ? `${committed} ${interim}`.trim() : committed).replace(
        /\s+/g,
        " ",
      );
      if (current) handlers.onInterim?.(current);
    };

    return {
      start() {
        if (listening) return;
        committed = "";
        recognition.start();
      },
      stop() {
        if (!listening) return;
        recognition.stop();
      },
      abort() {
        if (!listening) return;
        recognition.abort();
      },
      isListening() {
        return listening;
      },
    };
  }

  private static resolve(): (new () => SpeechRecognitionLike) | null {
    if (typeof window === "undefined") return null;
    const w = window as WindowWithSpeech;
    return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
  }
}
