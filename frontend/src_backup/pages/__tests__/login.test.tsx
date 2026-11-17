import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Shared mutable mock so tests can drive login outcome per case.
const authMock = vi.hoisted(() => ({
  user: null as { name: string } | null,
  loading: false,
  login: vi.fn(),
  sendOtp: vi.fn(),
  verifyOtp: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: (selector: (state: typeof authMock) => unknown) =>
    selector(authMock),
}));

import { LoginPage } from "@/pages/login";

function renderLogin() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <LoginPage /> },
      { path: "/login/mfa", element: <div>mfa-page</div> },
    ],
    { initialEntries: ["/login"] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

describe("LoginPage", () => {
  beforeEach(() => {
    authMock.user = null;
    authMock.loading = false;
    vi.clearAllMocks();
  });

  it("renders the password form by default", () => {
    renderLogin();

    expect(screen.getByLabelText("Phone or email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log in" })).toBeInTheDocument();
  });

  it("submits credentials and navigates home on success", async () => {
    const user = userEvent.setup();
    const router = renderLogin();
    authMock.login.mockResolvedValue("ok");

    await user.type(screen.getByLabelText("Phone or email"), "+919876543210");
    await user.type(screen.getByLabelText("Password"), "s3cret");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(authMock.login).toHaveBeenCalledWith(
      "+919876543210",
      "s3cret",
    );
    await vi.waitFor(() => {
      expect(router.state.location.pathname).toBe("/");
    });
  });

  it("routes to the MFA step when the account requires a challenge", async () => {
    const user = userEvent.setup();
    const router = renderLogin();
    authMock.login.mockResolvedValue("mfa");

    await user.type(screen.getByLabelText("Phone or email"), "farmer@example.com");
    await user.type(screen.getByLabelText("Password"), "s3cret");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    await vi.waitFor(() => {
      expect(router.state.location.pathname).toBe("/login/mfa");
    });
  });

  it("switches to the phone OTP tab and requires a 6-digit code to verify", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("tab", { name: "Phone OTP" }));
    const send = screen.getByRole("button", { name: "Send OTP" });

    await user.type(screen.getByLabelText("Phone number"), "9876543210");
    await user.click(send);

    expect(authMock.sendOtp).toHaveBeenCalledWith("9876543210");
    expect(screen.getByText(/OTP sent to 9876543210/)).toBeInTheDocument();

    // Verify stays disabled until a full 6-digit code is entered.
    const verify = screen.getByRole("button", { name: "Verify & log in" });
    expect(verify).toBeDisabled();
    await user.type(screen.getByLabelText("6-digit OTP"), "123");
    expect(verify).toBeDisabled();
    await user.type(screen.getByLabelText("6-digit OTP"), "456");
    expect(verify).toBeEnabled();
  });
});
