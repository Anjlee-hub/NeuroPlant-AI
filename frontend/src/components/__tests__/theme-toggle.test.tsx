import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { ThemeProvider } from "@/app/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";

function renderWithTheme() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  );
}

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("starts in light mode and toggles .dark on <html>", async () => {
    const user = userEvent.setup();
    renderWithTheme();

    const button = screen.getByRole("button", {
      name: "Switch to dark mode",
    });
    expect(button).toBeInTheDocument();

    await user.click(button);

    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("neuroplant-theme")).toBe("dark");
    expect(
      screen.getByRole("button", { name: "Switch to light mode" }),
    ).toBeInTheDocument();
  });

  it("flips back to light on a second click", async () => {
    const user = userEvent.setup();
    renderWithTheme();

    await user.click(screen.getByRole("button", { name: "Switch to dark mode" }));
    await user.click(screen.getByRole("button", { name: "Switch to light mode" }));

    expect(document.documentElement).not.toHaveClass("dark");
    expect(localStorage.getItem("neuroplant-theme")).toBe("light");
  });

  it("respects an existing dark preference stored in localStorage", () => {
    localStorage.setItem("neuroplant-theme", "dark");
    renderWithTheme();

    expect(document.documentElement).toHaveClass("dark");
    expect(
      screen.getByRole("button", { name: "Switch to light mode" }),
    ).toBeInTheDocument();
  });
});
