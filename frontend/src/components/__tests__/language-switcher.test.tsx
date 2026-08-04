import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import i18n from "@/i18n";
import { LanguageSwitcher } from "@/components/language-switcher";

describe("LanguageSwitcher", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    localStorage.clear();
  });

  it("renders every supported language as a selectable button", () => {
    render(<LanguageSwitcher />);
    expect(screen.getByRole("button", { name: "English" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "हिन्दी" })).toBeInTheDocument();
  });

  it("marks the active language and persists the choice to localStorage", async () => {
    const user = userEvent.setup();
    render(<LanguageSwitcher />);

    const en = screen.getByRole("button", { name: "English" });
    expect(en).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "हिन्दी" }));

    expect(en).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "हिन्दी" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(localStorage.getItem("i18nextLng")).toBe("hi");
  });

  it("keeps <html lang> in sync with the selected language", async () => {
    const user = userEvent.setup();
    render(<LanguageSwitcher />);

    expect(document.documentElement.lang).toBe("en");

    await user.click(screen.getByRole("button", { name: "हिन्दी" }));
    expect(document.documentElement.lang).toBe("hi");
  });
});
