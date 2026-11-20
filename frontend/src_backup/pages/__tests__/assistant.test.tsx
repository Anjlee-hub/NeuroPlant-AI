import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import type { AssistantReply } from "@/types/assistant";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  askAssistant: vi.fn(),
  getAssistantConversation: vi.fn(),
  clearAssistantConversation: vi.fn(),
}));
const synthMock = vi.hoisted(() => ({
  isSupported: vi.fn(() => true),
  speak: vi.fn(),
  cancel: vi.fn(),
}));
const recMock = vi.hoisted(() => ({
  isSupported: vi.fn(() => false),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));
vi.mock("@/services/speech-synthesis", () => ({
  SpeechSynthesisService: synthMock,
}));
vi.mock("@/services/speech-recognition", () => ({
  SpeechRecognitionService: recMock,
}));

import { AssistantPage } from "@/pages/assistant";

const reply: AssistantReply = {
  intent: "disease",
  lang: "en",
  message: "Your tomato has Early Blight.",
  sections: [{ title: "Overview", body: "A fungal disease caused by Alternaria." }],
};

const spokenText =
  "Your tomato has Early Blight.. Overview. A fungal disease caused by Alternaria.";

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/assistant", element: <AssistantPage /> },
    ],
    { initialEntries: ["/assistant"] },
  );
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("AssistantPage", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    vi.clearAllMocks();
    authMock.user = { id: 1, name: "Tester" };
    apiMock.askAssistant.mockResolvedValue(reply);
    apiMock.getAssistantConversation.mockResolvedValue({ items: [] });
    apiMock.clearAssistantConversation.mockResolvedValue(undefined);
    synthMock.isSupported.mockReturnValue(true);
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage();

    expect(await screen.findByText("Sign in to use the AI assistant.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("sends a suggestion chip and renders the reply aloud", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Ask your NeuroPlant assistant");
    await user.click(
      screen.getByRole("button", { name: "What disease does my crop have?" }),
    );

    // The user's question and the assistant's structured reply both render.
    expect(await screen.findByText("Your tomato has Early Blight.")).toBeInTheDocument();
    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("A fungal disease caused by Alternaria.")).toBeInTheDocument();

    // Voice output is on by default → the reply is read aloud in en-IN.
    expect(synthMock.speak).toHaveBeenCalledWith(spokenText, "en-IN", undefined);
  });

  it("sends a typed question via the send button", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Ask your NeuroPlant assistant");

    await user.type(screen.getByRole("textbox", { name: "Your question" }), "how do I treat it");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Your tomato has Early Blight.")).toBeInTheDocument();
    expect(apiMock.askAssistant).toHaveBeenCalledWith({
      query: "how do I treat it",
      lang: "en",
    });
  });

  it("does not read replies when voice output is turned off", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Ask your NeuroPlant assistant");

    await user.click(screen.getByRole("button", { name: "Voice replies" }));
    await user.click(
      screen.getByRole("button", { name: "What disease does my crop have?" }),
    );

    expect(await screen.findByText("Your tomato has Early Blight.")).toBeInTheDocument();
    expect(synthMock.speak).not.toHaveBeenCalled();
  });

  it("shows an error bubble when the backend fails", async () => {
    apiMock.askAssistant.mockRejectedValue(new Error("boom"));
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Ask your NeuroPlant assistant");

    await user.type(screen.getByRole("textbox", { name: "Your question" }), "hello");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByText("I couldn't get an answer right now. Please try again."),
    ).toBeInTheDocument();
  });

  it("clears the conversation and cancels any speech", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Ask your NeuroPlant assistant");

    await user.click(
      screen.getByRole("button", { name: "What disease does my crop have?" }),
    );
    await screen.findByText("Your tomato has Early Blight.");

    await user.click(screen.getByRole("button", { name: "Clear conversation" }));
    expect(synthMock.cancel).toHaveBeenCalled();
    expect(await screen.findByText("Ask your NeuroPlant assistant")).toBeInTheDocument();
  });

  it("restores the chat transcript on mount (M3.1 conversation memory)", async () => {
    apiMock.getAssistantConversation.mockResolvedValue({
      items: [
        {
          id: 1,
          role: "user",
          content: "My tomato has early blight",
          intent: null,
          lang: null,
          created_at: "2026-08-06T10:00:00Z",
        },
        {
          id: 2,
          role: "assistant",
          content: "Got it — Early Blight.",
          intent: "disease",
          lang: "en",
          created_at: "2026-08-06T10:00:01Z",
        },
      ],
    });
    renderPage();

    expect(await screen.findByText("My tomato has early blight")).toBeInTheDocument();
    expect(await screen.findByText("Got it — Early Blight.")).toBeInTheDocument();
    // Restored assistant turns bring their intent badge back too.
    expect(screen.getByText("Disease")).toBeInTheDocument();
  });

  it("clears the server transcript when the chat is cleared", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Ask your NeuroPlant assistant");

    await user.click(
      screen.getByRole("button", { name: "What disease does my crop have?" }),
    );
    await screen.findByText("Your tomato has Early Blight.");
    await user.click(screen.getByRole("button", { name: "Clear conversation" }));

    expect(apiMock.clearAssistantConversation).toHaveBeenCalledTimes(1);
  });
});
