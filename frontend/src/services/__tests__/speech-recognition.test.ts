import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  normalizeRecognitionError,
  SpeechRecognitionService,
  type SpeechRecognitionLike,
} from "@/services/speech-recognition";

/** The browser result-event shape, derived from the service's own interface. */
type RecognitionResultEvent = Parameters<
  NonNullable<SpeechRecognitionLike["onresult"]>
>[0];

/** Instances created by the stub, so tests can drive the recognizer. */
let instances: FakeRecognition[] = [];

/** A scripted fake of the browser `SpeechRecognition` for jsdom. */
class FakeRecognition implements SpeechRecognitionLike {
  lang = "";
  continuous = false;
  interimResults = false;
  maxAlternatives = 1;
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error?: string }) => void) | null = null;
  onresult: ((event: RecognitionResultEvent) => void) | null = null;

  start = vi.fn(() => this.onstart?.());
  stop = vi.fn(() => this.onend?.());
  abort = vi.fn(() => this.onend?.());

  constructor() {
    instances.push(this);
  }

  /** Drive a result batch like the browser would. */
  emitResult(entries: Array<{ transcript: string; isFinal: boolean }>) {
    const event = {
      resultIndex: 0,
      length: entries.length,
    } as unknown as RecognitionResultEvent;
    for (let i = 0; i < entries.length; i++) {
      (event as unknown as Array<unknown>)[i] = {
        isFinal: entries[i].isFinal,
        0: { transcript: entries[i].transcript },
      };
    }
    this.onresult?.(event);
  }
}

function stubSupported() {
  Object.defineProperty(window, "SpeechRecognition", {
    configurable: true,
    writable: true,
    value: FakeRecognition,
  });
}

function unsupported() {
  delete (window as { SpeechRecognition?: unknown }).SpeechRecognition;
}

beforeEach(() => {
  instances = [];
  stubSupported();
});

afterEach(() => {
  unsupported();
  vi.restoreAllMocks();
});

describe("SpeechRecognitionService", () => {
  it("reports support only when the browser API exists", () => {
    expect(SpeechRecognitionService.isSupported()).toBe(true);
    unsupported();
    expect(SpeechRecognitionService.isSupported()).toBe(false);
  });

  it("throws when the browser has no recognition API", () => {
    unsupported();
    expect(() => SpeechRecognitionService.create("en-IN")).toThrow();
  });

  it("configures the recognizer and wires start/stop lifecycle", () => {
    const onStart = vi.fn();
    const onEnd = vi.fn();
    const handle = SpeechRecognitionService.create("hi-IN", { onStart, onEnd });

    const rec = instances[0];
    expect(rec.lang).toBe("hi-IN");
    expect(rec.continuous).toBe(false);
    expect(rec.interimResults).toBe(true);
    expect(handle.isListening()).toBe(false);

    handle.start();
    expect(rec.start).toHaveBeenCalledTimes(1);
    expect(onStart).toHaveBeenCalledTimes(1);
    expect(handle.isListening()).toBe(true);

    handle.stop();
    expect(rec.stop).toHaveBeenCalledTimes(1);
    expect(onEnd).toHaveBeenCalledTimes(1);
    expect(handle.isListening()).toBe(false);
  });

  it("streams interim text and commits the final transcript", () => {
    const onInterim = vi.fn();
    const onFinal = vi.fn();
    const onEnd = vi.fn();
    const handle = SpeechRecognitionService.create("en-IN", {
      onInterim,
      onFinal,
      onEnd,
    });

    handle.start();
    const rec = instances[0];

    // Partial results stream live for instant feedback.
    rec.emitResult([{ transcript: "what disease", isFinal: false }]);
    expect(onInterim).toHaveBeenLastCalledWith("what disease");

    // The browser then finalizes the full sentence in one result.
    rec.emitResult([{ transcript: "what disease does my crop", isFinal: true }]);
    expect(onInterim).toHaveBeenLastCalledWith("what disease does my crop");

    handle.stop(); // fires onend → commits
    expect(onFinal).toHaveBeenCalledWith("what disease does my crop");
    expect(onEnd).toHaveBeenCalledTimes(1);
  });

  it("normalizes recognition errors to stable codes", () => {
    const onError = vi.fn();
    const handle = SpeechRecognitionService.create("en-IN", { onError });
    handle.start();

    instances[0].onerror?.({ error: "not-allowed" });
    expect(onError).toHaveBeenCalledWith("not-allowed");
  });

  it("aborts an in-flight session", () => {
    const handle = SpeechRecognitionService.create("en-IN");
    handle.start();
    handle.abort();
    expect(instances[0].abort).toHaveBeenCalledTimes(1);
  });
});

describe("normalizeRecognitionError", () => {
  it("maps vendor codes to a small localizable set", () => {
    expect(normalizeRecognitionError("not-allowed")).toBe("not-allowed");
    expect(normalizeRecognitionError("service-not-allowed")).toBe("not-allowed");
    expect(normalizeRecognitionError("no-speech")).toBe("no-speech");
    expect(normalizeRecognitionError("audio-capture")).toBe("audio-capture");
    expect(normalizeRecognitionError("network")).toBe("network");
    expect(normalizeRecognitionError("aborted")).toBe("aborted");
    expect(normalizeRecognitionError("bogus")).toBe("unknown");
    expect(normalizeRecognitionError(undefined)).toBe("unknown");
  });
});
