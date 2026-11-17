import { Stethoscope } from "lucide-react";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ComingSoonPage } from "@/pages/coming-soon";

function renderDoctor() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/doctor", element: <ComingSoonPage navKey="doctor" milestone="3" icon={Stethoscope} /> },
    ],
    { initialEntries: ["/doctor"] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

describe("ComingSoonPage", () => {
  it("tells the user what is coming and in which milestone", () => {
    renderDoctor();

    expect(
      screen.getByRole("heading", { name: /Crop Doctor/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Coming soon")).toBeInTheDocument();
    expect(screen.getByText("Planned for Milestone 3")).toBeInTheDocument();
    expect(screen.getByText("What's coming")).toBeInTheDocument();
    // At least one planned capability is listed.
    expect(
      screen.getByText(/Treatment recommendations/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
