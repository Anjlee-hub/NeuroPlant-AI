import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CommunityPost } from "@/types/community";

const authMock = vi.hoisted(() => ({
  user: { id: 1, name: "Farmer" } as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  listCommunityPosts: vi.fn(),
  listSavedCommunityPosts: vi.fn(),
  uploadCommunityPostImage: vi.fn(),
  createCommunityPost: vi.fn(),
  updateCommunityPost: vi.fn(),
  deleteCommunityPost: vi.fn(),
  voteForPost: vi.fn(),
  saveCommunityPost: vi.fn(),
  unsaveCommunityPost: vi.fn(),
  listPostComments: vi.fn(),
  addPostComment: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: (selector: (state: { user: typeof authMock.user }) => unknown) =>
    selector({ user: authMock.user }),
}));
vi.mock("@/lib/api", () => ({
  api: apiMock,
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
}));

import { CommunityPage } from "@/pages/community";

const post: CommunityPost = {
  id: 7,
  user_id: 1,
  title: "Tomato leaf spots",
  content: "Has anyone seen this on their crop?",
  image_url: null,
  category: "disease",
  is_active: true,
  created_at: "2026-11-18T10:00:00Z",
  farmer: { name: "Farmer", avatar_url: null },
  like_count: 2,
  is_liked: false,
  is_saved: false,
};

function renderCommunity() {
  const router = createMemoryRouter(
    [
      { path: "/community", element: <CommunityPage /> },
      { path: "/login", element: <div>login</div> },
    ],
    { initialEntries: ["/community"] },
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("CommunityPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMock.user = { id: 1, name: "Farmer" };
    apiMock.listCommunityPosts.mockResolvedValue([post]);
    apiMock.listSavedCommunityPosts.mockResolvedValue([]);
    apiMock.listPostComments.mockResolvedValue([]);
    apiMock.createCommunityPost.mockResolvedValue(post);
    apiMock.updateCommunityPost.mockResolvedValue(post);
    apiMock.deleteCommunityPost.mockResolvedValue(undefined);
    apiMock.voteForPost.mockResolvedValue({ like_count: 3, is_liked: true });
    apiMock.saveCommunityPost.mockResolvedValue({ saved: true });
    apiMock.unsaveCommunityPost.mockResolvedValue({ saved: false });
  });

  it("keeps the composer closed until requested and publishes from its modal", async () => {
    const user = userEvent.setup();
    renderCommunity();

    expect(await screen.findByText("Tomato leaf spots")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Create a post" }));
    const dialog = screen.getByRole("dialog");
    await user.type(
      within(dialog).getByLabelText("Title"),
      "New crop question",
    );
    await user.type(
      within(dialog).getByLabelText("Description"),
      "How often should I water?",
    );
    await user.click(within(dialog).getByRole("button", { name: "Publish Post" }));

    await waitFor(() => {
      expect(apiMock.createCommunityPost).toHaveBeenCalledWith({
        title: "New crop question",
        content: "How often should I water?",
        category: "general",
        image_url: undefined,
      });
    });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByRole("status")).toHaveTextContent("Your post was published.");
  });

  it("loads saved posts and lets the user persist a bookmark", async () => {
    const user = userEvent.setup();
    apiMock.listSavedCommunityPosts.mockResolvedValue([{ ...post, is_saved: true }]);
    renderCommunity();

    await screen.findByText("Tomato leaf spots");
    await user.click(screen.getByRole("button", { name: "Save post" }));
    await waitFor(() => expect(apiMock.saveCommunityPost).toHaveBeenCalledWith(7));

    await user.click(screen.getByRole("tab", { name: "Saved Posts" }));
    expect(await screen.findByRole("button", { name: "Remove saved post" })).toBeInTheDocument();
  });

  it("shows the API error and retries instead of showing an empty feed", async () => {
    const user = userEvent.setup();
    apiMock.listCommunityPosts
      .mockRejectedValueOnce(new Error("Service unavailable"))
      .mockResolvedValueOnce([post]);
    renderCommunity();

    expect(
      await screen.findByText("Could not load posts: Service unavailable"),
    ).toBeInTheDocument();
    expect(screen.queryByText("0 posts")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Tomato leaf spots")).toBeInTheDocument();
  });

  it("shows the backend reason when bookmark storage is unavailable", async () => {
    const user = userEvent.setup();
    apiMock.saveCommunityPost.mockRejectedValue(
      new Error("Community bookmarks require a database migration."),
    );
    renderCommunity();

    await screen.findByText("Tomato leaf spots");
    await user.click(screen.getByRole("button", { name: "Save post" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Community bookmarks require a database migration.",
    );
  });
});
