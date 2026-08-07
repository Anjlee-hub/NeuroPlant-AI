import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "@/components/marketplace/pagination";

describe("Pagination", () => {
  it("renders nothing when there is only one page", () => {
    const { container } = render(
      <Pagination page={1} pages={1} onPageChange={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("calls onPageChange with the next page", async () => {
    const onPageChange = vi.fn();
    render(<Pagination page={1} pages={3} onPageChange={onPageChange} />);

    await userEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("calls onPageChange with the previous page", async () => {
    const onPageChange = vi.fn();
    render(<Pagination page={2} pages={3} onPageChange={onPageChange} />);

    await userEvent.click(screen.getByRole("button", { name: "Previous" }));

    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("disables prev on the first page and next on the last page", () => {
    const { rerender } = render(
      <Pagination page={1} pages={3} onPageChange={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();

    rerender(<Pagination page={3} pages={3} onPageChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("marks the current page with aria-current and shows the page position", () => {
    render(<Pagination page={2} pages={5} onPageChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Go to page 2" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Page 2 of 5")).toBeInTheDocument();
  });

  it("does not navigate when clicking the current page", async () => {
    const onPageChange = vi.fn();
    render(<Pagination page={2} pages={3} onPageChange={onPageChange} />);

    await userEvent.click(screen.getByRole("button", { name: "Go to page 2" }));

    expect(onPageChange).not.toHaveBeenCalled();
  });
});
