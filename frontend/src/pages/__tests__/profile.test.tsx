import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/types/auth";

// Mutable mocks so tests can drive auth + API outcomes per case.
const authMock = vi.hoisted(() => ({
  user: null as User | null,
  updateUser: vi.fn(),
}));
const apiMock = vi.hoisted(() => ({
  listScans: vi.fn(),
  updateProfile: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({
    user: authMock.user,
    loading: false,
    updateUser: authMock.updateUser,
  }),
}));
vi.mock("@/lib/api", () => ({
  api: apiMock,
  errorMessage: (err: unknown) =>
    err instanceof Error ? err.message : "Request failed",
}));

import { ProfilePage } from "@/pages/profile";

const user: User = {
  id: 1,
  role: "farmer",
  phone: "+919876543210",
  email: "farmer@example.com",
  name: "Ravi Kumar",
  avatar_url: null,
  lang: "en",
  verified: true,
  created_at: "2026-06-01T08:00:00",
};

// page_size=1 — the profile only needs the `total` scan count.
const countList = {
  items: [],
  total: 7,
  page: 1,
  page_size: 1,
  has_next: false,
};

function renderProfile() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login-page</div> },
      { path: "/profile", element: <ProfilePage /> },
      { path: "/scans", element: <div>history-page</div> },
      { path: "/detect", element: <div>detect-page</div> },
    ],
    { initialEntries: ["/profile"] },
  );
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("ProfilePage", () => {
  beforeEach(() => {
    authMock.user = user;
    // Mirror the zustand store: updateUser merges a partial patch into state.
    authMock.updateUser.mockImplementation(
      (patch: Partial<User>) => {
        if (authMock.user) authMock.user = { ...authMock.user, ...patch };
      },
    );
    vi.clearAllMocks();
    authMock.updateUser.mockClear();
    apiMock.listScans.mockResolvedValue(countList);
  });

  it("requires sign-in when logged out", () => {
    authMock.user = null;
    renderProfile();
    expect(screen.getByText("Sign in to view your profile.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login",
    );
    expect(apiMock.listScans).not.toHaveBeenCalled();
  });

  it("shows identity, account details and the scan count", async () => {
    renderProfile();

    expect(screen.getByRole("heading", { name: "Ravi Kumar" })).toBeInTheDocument();
    // "Farmer" appears twice (identity card + role row) — assert both render.
    expect(screen.getAllByText("Farmer").length).toBeGreaterThan(0);
    expect(await screen.findByText("7 scans")).toBeInTheDocument();
    expect(screen.getByText("+919876543210")).toBeInTheDocument();
    expect(screen.getByText("farmer@example.com")).toBeInTheDocument();
    expect(screen.getByText("Member since")).toBeInTheDocument();
    // Quick links.
    expect(screen.getByRole("link", { name: "View scan history" })).toHaveAttribute(
      "href",
      "/scans",
    );
    expect(screen.getByRole("link", { name: "Scan a crop" })).toHaveAttribute(
      "href",
      "/detect",
    );
  });

  it("edits the profile name and syncs the store", async () => {
    const userEvt = userEvent.setup();
    apiMock.updateProfile.mockResolvedValue({ ...user, name: "Ravi Kumar Sharma" });

    renderProfile();

    await userEvt.click(screen.getByRole("button", { name: "Edit profile" }));
    const input = screen.getByLabelText("Full name");
    await userEvt.clear(input);
    await userEvt.type(input, "Ravi Kumar Sharma");
    await userEvt.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Profile updated.")).toBeInTheDocument();
    expect(apiMock.updateProfile).toHaveBeenCalledWith({ name: "Ravi Kumar Sharma" });
    expect(authMock.updateUser).toHaveBeenCalledWith({ name: "Ravi Kumar Sharma" });
    expect(screen.getByRole("heading", { name: "Ravi Kumar Sharma" })).toBeInTheDocument();
  });

  it("surfaces an error when saving the name fails", async () => {
    const userEvt = userEvent.setup();
    apiMock.updateProfile.mockRejectedValue(new Error("network down"));

    renderProfile();

    await userEvt.click(screen.getByRole("button", { name: "Edit profile" }));
    const input = screen.getByLabelText("Full name");
    await userEvt.clear(input);
    await userEvt.type(input, "New Name");
    await userEvt.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("network down")).toBeInTheDocument();
    expect(authMock.updateUser).not.toHaveBeenCalled();
  });
});
