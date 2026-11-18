import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SpeechSynthesisService } from "@/services/speech-synthesis";

/** Minimal fake of `SpeechSynthesisUtterance` for jsdom. */
class FakeUtterance {
  lang = "";
  rate = 1;
  pitch = 1;
  voice: SpeechSynthesisVoice | null = null;
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;
  text: string;

  constructor(text: string) {
    this.text = text;
    instances.push(this);
  }
}

let instances: FakeUtterance[] = [];

function fakeSynth(getVoices: () => SpeechSynthesisVoice[] = () => []) {
  const speechSynthesis = {
    speak: vi.fn(),
    cancel: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    getVoices: vi.fn(getVoices),
    speaking: false,
  };
  Object.defineProperty(window, "speechSynthesis", {
    configurable: true,
    writable: true,
    value: speechSynthesis,
  });
  vi.stubGlobal("SpeechSynthesisUtterance", FakeUtterance);
  return speechSynthesis;
}

function unsupported() {
  delete (window as { speechSynthesis?: unknown }).speechSynthesis;
  vi.unstubAllGlobals();
}

const voice = (lang: string, name: string): SpeechSynthesisVoice =>
  ({ lang, name, default: false, localService: false, voiceURI: name }) as SpeechSynthesisVoice;

beforeEach(() => {
  instances = [];
  fakeSynth();
  // voices() caches between calls; reset so each test starts cold.
  (SpeechSynthesisService as unknown as { voicesCache: unknown }).voicesCache = null;
});

afterEach(() => {
  unsupported();
  vi.restoreAllMocks();
});

describe("SpeechSynthesisService", () => {
  it("reports support only when the browser API exists", () => {
    expect(SpeechSynthesisService.isSupported()).toBe(true);
    unsupported();
    expect(SpeechSynthesisService.isSupported()).toBe(false);
  });

  it("reads text aloud in the requested locale and wires handlers", () => {
    const synth = fakeSynth(() => [voice("en-IN", "Indian English")]);
    const onStart = vi.fn();
    const onEnd = vi.fn();
    const onError = vi.fn();

    SpeechSynthesisService.speak("Hello", "en-IN", { onStart, onEnd, onError });

    expect(synth.cancel).toHaveBeenCalledTimes(1);
    expect(instances).toHaveLength(1);
    expect(instances[0].text).toBe("Hello");
    expect(instances[0].lang).toBe("en-IN");
    expect(instances[0].voice?.lang).toBe("en-IN");
    expect(synth.speak).toHaveBeenCalledWith(instances[0]);

    instances[0].onstart?.();
    expect(onStart).toHaveBeenCalledTimes(1);
    instances[0].onend?.();
    expect(onEnd).toHaveBeenCalledTimes(1);
    instances[0].onerror?.();
    expect(onError).toHaveBeenCalledTimes(1);
  });

  it("skips empty or unsupported reads", () => {
    const synth = fakeSynth();
    SpeechSynthesisService.speak("   ", "en");
    expect(synth.speak).not.toHaveBeenCalled();

    unsupported();
    SpeechSynthesisService.speak("hello", "en");
    expect(synth.speak).not.toHaveBeenCalled();
  });

  it("picks the exact voice match before a prefix fallback", () => {
    fakeSynth(() => [
      voice("hi-IN", "Hindi"),
      voice("hi", "Hindi Generic"),
      voice("en-IN", "Indian English"),
    ]);
    expect(SpeechSynthesisService.pickVoice("hi-IN")?.name).toBe("Hindi");
    // "hi" exact-matches the generic "hi" voice — exact wins over the hi-IN prefix.
    expect(SpeechSynthesisService.pickVoice("hi")?.name).toBe("Hindi Generic");
    // "en" has no exact match → falls back to the first en* voice.
    expect(SpeechSynthesisService.pickVoice("en")?.name).toBe("Indian English");
    // No voice shares a prefix with "bn" → null.
    expect(SpeechSynthesisService.pickVoice("bn")).toBeNull();
  });

  it("returns null when no voice matches the locale", () => {
    fakeSynth(() => [voice("ta-IN", "Tamil")]);
    expect(SpeechSynthesisService.pickVoice("en")).toBeNull();
  });

  it("returns null when no voices are available", () => {
    fakeSynth(() => []);
    expect(SpeechSynthesisService.pickVoice("en-IN")).toBeNull();
  });

  it("delegates cancel / pause / resume / isSpeaking to the browser", () => {
    const synth = fakeSynth();
    SpeechSynthesisService.cancel();
    SpeechSynthesisService.pause();
    SpeechSynthesisService.resume();
    expect(synth.cancel).toHaveBeenCalledTimes(1);
    expect(synth.pause).toHaveBeenCalledTimes(1);
    expect(synth.resume).toHaveBeenCalledTimes(1);

    synth.speaking = true;
    expect(SpeechSynthesisService.isSpeaking()).toBe(true);
    synth.speaking = false;
    expect(SpeechSynthesisService.isSpeaking()).toBe(false);
  });
});
