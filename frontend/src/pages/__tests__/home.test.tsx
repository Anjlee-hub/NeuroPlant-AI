import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { HomePage } from "@/pages/home";

function renderHome() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <HomePage /> },
      { path: "/detect", element: <div>detect-page</div> },
      { path: "/register", element: <div>register-page</div> },
    ],
    { initialEntries: ["/"] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

describe("HomePage", () => {
  it("renders the hero title and both call-to-action links", () => {
    renderHome();

    expect(
      screen.getByRole("heading", {
        name: "Healthy crops, higher yields, for every Indian farmer",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Scan a leaf" })).toHaveAttribute(
      "href",
      "/detect",
    );
    expect(
      screen.getByRole("link", { name: "Ask the AI assistant" }),
    ).toHaveAttribute("href", "/register");
  });

  it("renders the feature cards with a proper heading hierarchy", () => {
    renderHome();

    // Section header is an h2; each feature title is an h3.
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Everything a farm needs, in one app",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "AI disease detection" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "Speaks 12 languages" }),
    ).toBeInTheDocument();
  });
});
