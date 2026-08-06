import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AssistantReply } from "@/types/assistant";

vi.mock("@/lib/api", () => ({
  api: {
    askAssistant: vi.fn(),
    getAssistantConversation: vi.fn(),
    clearAssistantConversation: vi.fn(),
  },
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
const mockedList = vi.mocked(api.getAssistantConversation);
const mockedClear = vi.mocked(api.clearAssistantConversation);
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

  it("restores and clears the persisted conversation", async () => {
    mockedList.mockResolvedValue({
      items: [
        {
          id: 1,
          role: "user",
          content: "Hello!",
          intent: null,
          lang: null,
          created_at: "2026-08-06T10:00:00Z",
        },
      ],
    });
    await expect(VoiceAssistantService.listConversation()).resolves.toMatchObject({
      items: [{ role: "user", content: "Hello!" }],
    });
    expect(mockedList).toHaveBeenCalledTimes(1);

    mockedClear.mockResolvedValue(undefined);
    await expect(VoiceAssistantService.clearConversation()).resolves.toBeUndefined();
    expect(mockedClear).toHaveBeenCalledTimes(1);
  });
});
