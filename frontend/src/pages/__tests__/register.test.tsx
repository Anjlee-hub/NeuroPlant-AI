import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Shared mutable mock so tests can drive the registration outcome per case.
const authMock = vi.hoisted(() => ({
  user: null as { name: string } | null,
  loading: false,
  register: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: (selector: (state: typeof authMock) => unknown) =>
    selector(authMock),
}));
vi.mock("@/lib/api", () => ({
  errorMessage: (err: unknown) =>
    err instanceof Error ? err.message : "Request failed",
}));

import { RegisterPage } from "@/pages/register";

function renderRegister() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/register", element: <RegisterPage /> },
    ],
    { initialEntries: ["/register"] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

describe("RegisterPage", () => {
  beforeEach(() => {
    authMock.user = null;
    authMock.loading = false;
    vi.clearAllMocks();
  });

  it("renders the form with role options, defaulting to Farmer", () => {
    renderRegister();

    expect(screen.getByLabelText("Full name")).toBeInTheDocument();
    expect(screen.getByLabelText("Phone number")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Farmer" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: "Expert" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign up" })).toBeInTheDocument();
  });

  it("submits the profile and navigates home on success", async () => {
    const user = userEvent.setup();
    const router = renderRegister();
    authMock.register.mockResolvedValue(undefined);

    await user.type(screen.getByLabelText("Full name"), "Ravi Kumar");
    await user.type(screen.getByLabelText("Phone number"), "+919876543210");
    await user.click(screen.getByRole("button", { name: "Sign up" }));

    expect(authMock.register).toHaveBeenCalledWith({
      name: "Ravi Kumar",
      phone: "+919876543210",
      role: "farmer",
      email: undefined,
      password: undefined,
    });
    await vi.waitFor(() => expect(router.state.location.pathname).toBe("/"));
  });

  it("switches the role and surfaces server errors", async () => {
    const user = userEvent.setup();
    renderRegister();
    authMock.register.mockRejectedValue(new Error("phone already registered"));

    await user.click(screen.getByRole("radio", { name: "Expert" }));
    expect(screen.getByRole("radio", { name: "Expert" })).toHaveAttribute(
      "aria-checked",
      "true",
    );

    await user.type(screen.getByLabelText("Full name"), "Dr. Asha");
    await user.type(screen.getByLabelText("Phone number"), "+919876543211");
    await user.click(screen.getByRole("button", { name: "Sign up" }));

    expect(
      await screen.findByText("phone already registered"),
    ).toBeInTheDocument();
  });
});
