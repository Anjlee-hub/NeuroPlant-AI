/**
 * Text-to-speech service (M3, Task 6) — a thin, UI-free wrapper over the
 * browser's Web Speech synthesis API (`window.speechSynthesis`). It picks the
 * best available voice for a BCP-47 locale (exact match first, then any voice
 * with the same language prefix), reads a string aloud, and lets callers
 * cancel / pause / resume. When the API is missing (jsdom, older browsers)
 * `isSupported()` is false and the SpeakButton renders nothing.
 *
 * Framework-free like its sibling SpeechRecognitionService: the UI layer only
 * forwards text + locale and maps completion/error events to its own state.
 */

export interface SpeechSynthesisHandlers {
  onStart?: () => void;
  onEnd?: () => void;
  onError?: () => void;
}

export class SpeechSynthesisService {
  private static voicesCache: SpeechSynthesisVoice[] | null = null;

  /** True when this browser ships the Web Speech synthesis API. */
  static isSupported(): boolean {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  /** Cached voice list (refreshed when the browser reports a change). */
  static voices(): SpeechSynthesisVoice[] {
    if (!SpeechSynthesisService.isSupported()) return [];
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) SpeechSynthesisService.voicesCache = voices;
    return SpeechSynthesisService.voicesCache ?? [];
  }

  /**
   * Pick the voice closest to `lang` (BCP-47, e.g. "hi-IN"): exact match
   * first, then the first voice whose language shares the prefix ("hi").
   */
  static pickVoice(lang: string): SpeechSynthesisVoice | null {
    const voices = SpeechSynthesisService.voices();
    if (voices.length === 0) return null;
    const normalized = lang.toLowerCase().replace("_", "-");
    const exact = voices.find(
      (voice) => voice.lang.toLowerCase().replace("_", "-") === normalized,
    );
    if (exact) return exact;
    const prefix = normalized.split("-")[0];
    return voices.find((voice) => voice.lang.toLowerCase().startsWith(prefix)) ?? null;
  }

  /** Read `text` aloud in `lang`, cancelling anything already playing. */
  static speak(text: string, lang: string, handlers: SpeechSynthesisHandlers = {}): void {
    if (!SpeechSynthesisService.isSupported() || !text.trim()) return;
    SpeechSynthesisService.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    const voice = SpeechSynthesisService.pickVoice(lang);
    if (voice) utterance.voice = voice;
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.onstart = () => handlers.onStart?.();
    utterance.onend = () => handlers.onEnd?.();
    utterance.onerror = () => handlers.onError?.();
    window.speechSynthesis.speak(utterance);
  }

  static cancel(): void {
    if (!SpeechSynthesisService.isSupported()) return;
    window.speechSynthesis.cancel();
  }

  static pause(): void {
    if (!SpeechSynthesisService.isSupported()) return;
    window.speechSynthesis.pause();
  }

  static resume(): void {
    if (!SpeechSynthesisService.isSupported()) return;
    window.speechSynthesis.resume();
  }

  static isSpeaking(): boolean {
    return SpeechSynthesisService.isSupported() && window.speechSynthesis.speaking;
  }
}
