import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import { SpeechInput } from "@/components/assistant/speech-input";

interface SpeechRecognitionHandlersLike {
  onStart?: () => void;
  onInterim?: (text: string) => void;
  onFinal?: (text: string) => void;
  onEnd?: () => void;
  onError?: (code: string) => void;
}

const recMock = vi.hoisted(() => ({
  isSupported: vi.fn(() => true),
  create: vi.fn(),
}));

vi.mock("@/services/speech-recognition", () => ({
  SpeechRecognitionService: recMock,
}));

function makeHandle() {
  return {
    start: vi.fn(),
    stop: vi.fn(),
    abort: vi.fn(),
    isListening: vi.fn(() => false),
  };
}

/** Controlled wrapper so tests can observe committed transcripts. */
function Wrapper({ onSubmit }: { onSubmit?: () => void }) {
  const [value, setValue] = useState("");
  return (
    <SpeechInput
      value={value}
      onChange={setValue}
      onSubmit={onSubmit}
      ariaLabel="Your question"
    />
  );
}

let handlers: SpeechRecognitionHandlersLike | undefined;
let handle: ReturnType<typeof makeHandle>;

beforeEach(async () => {
  await i18n.changeLanguage("en");
  vi.clearAllMocks();
  handlers = undefined;
  handle = makeHandle();
  recMock.isSupported.mockReturnValue(true);
  recMock.create.mockImplementation((_lang: string, h: SpeechRecognitionHandlersLike) => {
    handlers = h;
    return handle;
  });
});

describe("SpeechInput", () => {
  it("renders a disabled mic when recognition is unsupported", () => {
    recMock.isSupported.mockReturnValue(false);
    render(<Wrapper />);

    const mic = screen.getByRole("button", {
      name: "Voice input isn't supported in this browser.",
    });
    expect(mic).toBeDisabled();
  });

  it("starts and stops a recognition session from the mic toggle", async () => {
    const user = userEvent.setup();
    render(<Wrapper />);

    await user.click(screen.getByRole("button", { name: "Speak your question" }));
    expect(recMock.create).toHaveBeenCalledWith("en-IN", expect.anything());
    expect(handle.start).toHaveBeenCalledTimes(1);

    act(() => handlers?.onStart?.());
    expect(screen.getByRole("button", { name: "Stop listening" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Stop listening" }));
    expect(handle.stop).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Speak your question" })).toBeInTheDocument();
  });

  it("streams interim text live and commits the final transcript", async () => {
    const user = userEvent.setup();
    render(<Wrapper />);

    await user.click(screen.getByRole("button", { name: "Speak your question" }));
    act(() => handlers?.onStart?.());

    const input = screen.getByRole("textbox", { name: "Your question" });
    act(() => handlers?.onInterim?.("what disease"));
    expect(input).toHaveValue("what disease");

    // A final result is committed via onChange; once recognition ends the input
    // reflects the committed transcript rather than the cleared live text.
    act(() => handlers?.onFinal?.("what disease does my crop"));
    act(() => handlers?.onEnd?.());
    expect(input).toHaveValue("what disease does my crop");
  });

  it("surfaces localized recognition errors as an alert", async () => {
    const user = userEvent.setup();
    render(<Wrapper />);

    await user.click(screen.getByRole("button", { name: "Speak your question" }));
    act(() => handlers?.onError?.("not-allowed"));

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent("Microphone access was denied. Allow it in your browser settings and try again.");
  });

  it("submits the typed text on Enter", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<Wrapper onSubmit={onSubmit} />);

    const input = screen.getByRole("textbox", { name: "Your question" });
    await user.type(input, "fertilizer advice{enter}");
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
