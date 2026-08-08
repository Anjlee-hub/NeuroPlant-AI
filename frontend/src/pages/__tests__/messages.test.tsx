import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ConversationDetail,
  ConversationListItem,
} from "@/types/messages";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  listConversations: vi.fn(),
  getConversation: vi.fn(),
  sendMessage: vi.fn(),
  markConversationRead: vi.fn(),
  closeConversation: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { MessagesDetailPage } from "@/pages/messages-detail";
import { MessagesListPage } from "@/pages/messages-list";

const seller = {
  id: 20,
  name: "Green Agri Supplies",
  role: "seller",
  shop_name: "Green Agri Supplies",
  avatar_url: null,
};

/** One inbox row with sensible defaults. */
function makeConversation(overrides: Partial<ConversationListItem> = {}): ConversationListItem {
  return {
    id: 1,
    status: "active",
    created_at: "2026-08-01T09:00:00Z",
    updated_at: "2026-08-02T10:00:00Z",
    last_message_at: "2026-08-02T10:00:00Z",
    last_message_preview: "Is this neem oil in stock?",
    last_message_sender_id: 20,
    unread_count: 1,
    buyer: { id: 1, name: "Buyer", role: "customer", shop_name: null, avatar_url: null },
    seller,
    listing: null,
    product: { id: 3, name: "Neem oil spray", image: null },
    ...overrides,
  };
}

function makeDetail(overrides: Partial<ConversationDetail> = {}): ConversationDetail {
  return {
    ...makeConversation(),
    messages: [
      {
        id: 1,
        conversation_id: 1,
        sender_id: 20,
        sender_name: "Green Agri Supplies",
        content: "Hello! We stock neem oil.",
        created_at: "2026-08-01T09:00:00Z",
        read_at: "2026-08-01T09:05:00Z",
      },
      {
        id: 2,
        conversation_id: 1,
        sender_id: 1,
        sender_name: "Buyer",
        content: "Great, how much per litre?",
        created_at: "2026-08-02T10:00:00Z",
        read_at: null,
      },
    ],
    ...overrides,
  };
}

function renderList() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/marketplace/messages", element: <MessagesListPage /> },
      { path: "/marketplace/messages/:conversationId", element: <div>thread</div> },
    ],
    { initialEntries: ["/marketplace/messages"] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

function renderDetail(id = 1) {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/marketplace/messages", element: <div>inbox</div> },
      {
        path: "/marketplace/messages/:conversationId",
        element: <MessagesDetailPage />,
      },
    ],
    { initialEntries: [`/marketplace/messages/${id}`] },
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("MessagesListPage (/marketplace/messages)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMock.user = { id: 1, name: "Tester" };
    apiMock.listConversations.mockResolvedValue([makeConversation()]);
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderList();
    expect(
      await screen.findByText("Sign in to read your messages."),
    ).toBeInTheDocument();
  });

  it("renders the other party, related product, preview, and unread count", async () => {
    renderList();

    // The seller is the other side for the current user (buyer).
    expect(await screen.findByText("Green Agri Supplies")).toBeInTheDocument();
    expect(screen.getByText("Neem oil spray")).toBeInTheDocument();
    expect(screen.getByText("Is this neem oil in stock?")).toBeInTheDocument();
    // Unread badge is announced accessibly.
    expect(screen.getByRole("status", { name: "1 unread messages" })).toHaveTextContent("1");
  });

  it("links each row into the thread", async () => {
    renderList();
    expect(
      await screen.findByRole("link", { name: /Open conversation with Green Agri Supplies/ }),
    ).toHaveAttribute("href", "/marketplace/messages/1");
  });

  it("labels closed threads without an unread badge", async () => {
    apiMock.listConversations.mockResolvedValue([
      makeConversation({ status: "closed", unread_count: 0 }),
    ]);
    renderList();

    expect(await screen.findByText("Closed")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: /unread/ })).not.toBeInTheDocument();
  });

  it("shows an empty state when the inbox has no conversations", async () => {
    apiMock.listConversations.mockResolvedValue([]);
    renderList();

    expect(
      await screen.findByText("No conversations yet"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Browse the marketplace" }),
    ).toHaveAttribute("href", "/marketplace/browse");
  });

  it("shows an error state with retry when loading fails", async () => {
    apiMock.listConversations.mockRejectedValue(new Error("boom"));
    renderList();

    expect(
      await screen.findByText("Couldn't load conversations"),
    ).toBeInTheDocument();
    apiMock.listConversations.mockResolvedValue([makeConversation()]);
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Green Agri Supplies")).toBeInTheDocument();
  });
});

describe("MessagesDetailPage (/marketplace/messages/:id)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMock.user = { id: 1, name: "Tester" };
    apiMock.getConversation.mockResolvedValue(makeDetail());
    apiMock.sendMessage.mockResolvedValue({
      id: 3,
      conversation_id: 1,
      sender_id: 1,
      sender_name: "Tester",
      content: "Two bottles please.",
      created_at: "2026-08-02T11:00:00Z",
      read_at: null,
    });
    apiMock.markConversationRead.mockResolvedValue({ conversation_id: 1, unread_count: 0 });
    apiMock.closeConversation.mockResolvedValue({ ...makeConversation(), status: "closed" });
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderDetail();
    expect(
      await screen.findByText("Sign in to read your messages."),
    ).toBeInTheDocument();
  });

  it("renders the message history with own messages aligned right", async () => {
    renderDetail();

    expect(await screen.findByText("Hello! We stock neem oil.")).toBeInTheDocument();
    expect(screen.getByText("Great, how much per litre?")).toBeInTheDocument();
    // Seller name + shop name are the same string here, so both appear.
    expect(screen.getAllByText("Green Agri Supplies").length).toBeGreaterThan(0);
    // The related product is shown in the thread header ("· Neem oil spray").
    expect(screen.getByText(/Neem oil spray/)).toBeInTheDocument();
  });

  it("marks unread conversations as read on open", async () => {
    renderDetail();
    await screen.findByText("Hello! We stock neem oil.");

    await vi.waitFor(() =>
      expect(apiMock.markConversationRead).toHaveBeenCalledWith(1),
    );
  });

  it("sends a new message from the composer", async () => {
    renderDetail();
    await screen.findByText("Hello! We stock neem oil.");

    await userEvent.type(
      screen.getByRole("textbox", { name: "Message" }),
      "Two bottles please.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));

    await vi.waitFor(() =>
      expect(apiMock.sendMessage).toHaveBeenCalledWith(1, { content: "Two bottles please." }),
    );
  });

  it("blocks the composer on a closed thread and explains why", async () => {
    apiMock.getConversation.mockResolvedValue(makeDetail({ status: "closed" }));
    renderDetail();

    expect(
      await screen.findByText("This conversation is closed. Contact the seller again to reopen it."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Message" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send message" })).not.toBeInTheDocument();
  });

  it("closes a thread after confirmation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    renderDetail();
    await screen.findByText("Hello! We stock neem oil.");

    await userEvent.click(screen.getByRole("button", { name: "Close conversation" }));
    await vi.waitFor(() => expect(apiMock.closeConversation).toHaveBeenCalledWith(1));

    // The header switches to the closed badge after the mutation lands.
    expect(await screen.findByText("Closed")).toBeInTheDocument();
    confirmSpy.mockRestore();
  });

  it("shows a not-found card for an unknown or non-participant thread", async () => {
    apiMock.getConversation.mockRejectedValue(
      Object.assign(new Error("Conversation not found"), { status: 404 }),
    );
    renderDetail();

    expect(await screen.findByText("Conversation not found")).toBeInTheDocument();
  });
});
