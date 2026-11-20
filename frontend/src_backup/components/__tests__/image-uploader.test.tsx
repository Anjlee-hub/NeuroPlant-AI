import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMock = vi.hoisted(() => ({
  uploadListingImages: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMock }));

import { ListingImageUploader } from "@/components/marketplace/image-uploader";

/** A valid PNG file (type + size are what the component checks). */
function pngFile(name = "photo.png", size = 1024): File {
  return new File([new Uint8Array(size)], name, { type: "image/png" });
}

function pickFile(file: File) {
  const input = screen.getByLabelText("Add photos");
  return userEvent.upload(input, file);
}

describe("ListingImageUploader", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.uploadListingImages.mockResolvedValue({ urls: ["/media/marketplace/uploaded.png"] });
  });

  it("renders persisted URLs with a remove affordance and reports removal", async () => {
    const onChange = vi.fn();
    const { container } = render(
      <ListingImageUploader initialUrls={["/media/a.png"]} onChange={onChange} />,
    );

    expect(container.querySelector("img")).toHaveAttribute("src", "/media/a.png");
    await userEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("uploads the picked batch and reports the persisted URLs", async () => {
    const onChange = vi.fn();
    const { container } = render(<ListingImageUploader onChange={onChange} />);

    await pickFile(pngFile());
    // The pending thumbnail previews via the stubbed blob URL.
    expect(container.querySelector("img")).toHaveAttribute("src", "blob:test-preview");

    // After picking, the batch-upload button appears next to the add tile.
    const uploadButton = screen.getAllByRole("button", { name: "Add photos" })[1];
    await userEvent.click(uploadButton);

    await waitFor(() => expect(apiMock.uploadListingImages).toHaveBeenCalledTimes(1));
    const files = apiMock.uploadListingImages.mock.calls[0][0] as File[];
    expect(files).toHaveLength(1);
    expect(files[0].name).toBe("photo.png");
    expect(onChange).toHaveBeenCalledWith(["/media/marketplace/uploaded.png"]);
  });

  it("rejects more than 8 images as a batch", async () => {
    render(<ListingImageUploader onChange={vi.fn()} />);

    const input = screen.getByLabelText("Add photos");
    await userEvent.upload(input, Array.from({ length: 9 }, (_, i) => pngFile(`${i}.png`)));

    expect(screen.getByText("You can add at most 8 photos.")).toBeInTheDocument();
    expect(apiMock.uploadListingImages).not.toHaveBeenCalled();
  });

  it("rejects an oversized image before upload", async () => {
    render(<ListingImageUploader onChange={vi.fn()} />);
    await pickFile(pngFile("big.png", 10 * 1024 * 1024 + 1));
    expect(screen.getByText("This photo is larger than 10 MB.")).toBeInTheDocument();
    expect(apiMock.uploadListingImages).not.toHaveBeenCalled();
  });

  it("rejects a non-image before upload (accept filter bypassed, as iOS 'All files' does)", async () => {
    render(<ListingImageUploader onChange={vi.fn()} />);

    // fireEvent bypasses the input's `accept` (userEvent filters by it), which
    // is exactly the "pick all files" path mobile browsers allow.
    const input = screen.getByLabelText("Add photos");
    fireEvent.change(input, {
      target: { files: [new File([new Uint8Array(8)], "notes.txt", { type: "text/plain" })] },
    });

    expect(screen.getByText("Only JPEG, PNG or WebP images are allowed.")).toBeInTheDocument();
    expect(apiMock.uploadListingImages).not.toHaveBeenCalled();
  });

  it("hides the add tile once the listing is at the 8-image cap", () => {
    const urls = Array.from({ length: 8 }, (_, i) => `/media/marketplace/${i}.png`);
    render(<ListingImageUploader initialUrls={urls} onChange={vi.fn()} />);

    expect(screen.queryByRole("button", { name: "Add photos" })).not.toBeInTheDocument();
  });
});
