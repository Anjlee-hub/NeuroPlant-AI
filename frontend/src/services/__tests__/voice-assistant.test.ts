import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AssistantReply } from "@/types/assistant";

vi.mock("@/lib/api", () => ({
  api: { askAssistant: vi.fn() },
}));

vi.mock("@/services/speech-synthesis", () => ({
  SpeechSynthesisService: {
    speak: vi.fn(),
    isSupported: vi.fn(() => true),
  },
}));

vi.mock("@/services/speech-recognition", () => ({
  SpeechRecognitionService: {
    isSupported: vi.fn(() => false),
  },
}));

import { api } from "@/lib/api";
import { SpeechSynthesisService } from "@/services/speech-synthesis";
import {
  replyText,
  speechLocale,
  VoiceAssistantService,
} from "@/services/voice-assistant";

const mockedAsk = vi.mocked(api.askAssistant);
const mockedSpeak = vi.mocked(SpeechSynthesisService.speak);

const hiReply: AssistantReply = {
  intent: "treatment",
  lang: "hi",
  message: "आपकी फसल का इलाज",
  sections: [{ title: "घरेलू उपाय", body: "नीम का तेल छिड़कें" }],
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("speechLocale", () => {
  it("maps the supported app languages to Indian voice locales", () => {
    expect(speechLocale("en")).toBe("en-IN");
    expect(speechLocale("hi")).toBe("hi-IN");
  });

  it("passes through unmapped codes (future languages, M4)", () => {
    expect(speechLocale("ta")).toBe("ta");
  });
});

describe("replyText", () => {
  it("joins the message and each section into one speakable string", () => {
    expect(replyText(hiReply)).toBe(
      "आपकी फसल का इलाज. घरेलू उपाय. नीम का तेल छिड़कें",
    );
  });

  it("skips empty parts", () => {
    expect(
      replyText({
        intent: "help",
        lang: "en",
        message: "How can I help?",
        sections: [],
      }),
    ).toBe("How can I help?");
  });
});

describe("VoiceAssistantService", () => {
  it("sends the query to the backend with its language", async () => {
    mockedAsk.mockResolvedValue(hiReply);
    await expect(VoiceAssistantService.ask("क्या करूं", "hi")).resolves.toBe(hiReply);
    expect(mockedAsk).toHaveBeenCalledWith({ query: "क्या करूं", lang: "hi" });
  });

  it("reads a reply aloud in the reply's own language", () => {
    VoiceAssistantService.readReply(hiReply);
    expect(mockedSpeak).toHaveBeenCalledWith(
      "आपकी फसल का इलाज. घरेलू उपाय. नीम का तेल छिड़कें",
      "hi-IN",
      undefined,
    );
  });

  it("reports voice support when either speech API exists", () => {
    expect(VoiceAssistantService.isVoiceSupported()).toBe(true); // synthesis stubbed
  });
});
