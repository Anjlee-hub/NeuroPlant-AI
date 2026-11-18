import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import { SpeakButton } from "@/components/assistant/speak-button";

/** The last utterance passed to the browser, so tests can fire onend/onerror. */
interface UtteranceLike {
  text: string;
  lang: string;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}
let lastUtterance: UtteranceLike | null = null;
const speak = vi.fn((utterance: UtteranceLike) => {
  lastUtterance = utterance;
});
const cancel = vi.fn();

function stubSynth() {
  Object.defineProperty(window, "speechSynthesis", {
    configurable: true,
    writable: true,
    value: {
      speak,
      cancel,
      pause: vi.fn(),
      resume: vi.fn(),
      getVoices: vi.fn(() => []),
      speaking: false,
    },
  });
  vi.stubGlobal(
    "SpeechSynthesisUtterance",
    class {
      lang = "";
      rate = 1;
      pitch = 1;
      voice = null;
      onstart: (() => void) | null = null;
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(public text: string) {}
    },
  );
}

function unsupported() {
  delete (window as { speechSynthesis?: unknown }).speechSynthesis;
  vi.unstubAllGlobals();
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  lastUtterance = null;
  speak.mockClear();
  cancel.mockClear();
  stubSynth();
});

afterEach(() => {
  unsupported();
  vi.restoreAllMocks();
});

describe("SpeakButton", () => {
  it("renders nothing when the browser has no speech synthesis", () => {
    unsupported();
    const { container } = render(<SpeakButton text="hello" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing for empty text", () => {
    const { container } = render(<SpeakButton text="   " />);
    expect(container.firstChild).toBeNull();
  });

  it("plays the text and toggles to a stop control", async () => {
    const user = userEvent.setup();
    render(<SpeakButton text="Water the tomato plants" />);

    const button = screen.getByRole("button", { name: "Read aloud" });
    await user.click(button);

    expect(speak).toHaveBeenCalledTimes(1);
    expect(lastUtterance?.text).toBe("Water the tomato plants");
    expect(lastUtterance?.lang).toBe("en-IN");
    expect(button).toHaveAttribute("aria-pressed", "true");

    // The service cancels any in-flight speech before reading; clear that so
    // this click is only the user's explicit stop.
    cancel.mockClear();
    await user.click(button);
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(button).toHaveAttribute("aria-pressed", "false");
  });

  it("resets after the speech finishes so it can replay", async () => {
    const user = userEvent.setup();
    render(<SpeakButton text="replay me" />);

    const button = screen.getByRole("button", { name: "Read aloud" });
    await user.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");

    act(() => lastUtterance?.onend?.());
    expect(button).toHaveAttribute("aria-pressed", "false");
  });

  it("accepts a custom label and resolves the language to a voice locale", async () => {
    const user = userEvent.setup();
    render(<SpeakButton text="पौधों को पानी दें" lang="hi" label="सुनें" />);

    await user.click(screen.getByRole("button", { name: "सुनें" }));
    expect(lastUtterance?.text).toBe("पौधों को पानी दें");
    expect(lastUtterance?.lang).toBe("hi-IN");
  });
});
