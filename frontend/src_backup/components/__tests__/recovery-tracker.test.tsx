import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RecoveryTrackerPanel } from "@/components/doctor/recovery-tracker";
import { api } from "@/lib/api";
import type { RecoveryLogInput, RecoveryTracker } from "@/types/recovery";

vi.mock("@/lib/api", () => ({
  api: {
    getScanRecoveryTracker: vi.fn(),
    addRecoveryLog: vi.fn(),
    updateRecoveryLog: vi.fn(),
    deleteRecoveryLog: vi.fn(),
  },
}));

const mockTracker: RecoveryTracker = {
  scan: {
    id: 7,
    disease_name: "Early Blight",
    crop_id: 1,
    crop_name: "Tomato",
    part_type: "leaf",
    severity: "severe",
    stage: "early",
    confidence: 0.92,
    provider: "tflite",
    model_version: "1.0",
    created_at: "2026-08-06T09:00:00Z",
  },
  risk: "high",
  recovery_percentage: 0.4,
  status: "on_track",
  total_treatments: 1,
  timeline: [
    {
      id: 1,
      scan_id: 7,
      treatment_applied: "Neem oil spray",
      notes: "Sprayed both sides",
      progress: "improving",
      applied_at: "2026-08-06T09:30:00Z",
      created_at: "2026-08-06T09:30:00Z",
    },
  ],
  updated_at: "2026-08-06T09:30:00Z",
};

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const getScanRecoveryTracker = api.getScanRecoveryTracker as ReturnType<typeof vi.fn>;
const addRecoveryLog = api.addRecoveryLog as ReturnType<typeof vi.fn>;
const updateRecoveryLog = api.updateRecoveryLog as ReturnType<typeof vi.fn>;
const deleteRecoveryLog = api.deleteRecoveryLog as ReturnType<typeof vi.fn>;

describe("RecoveryTrackerPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading skeleton while the request is pending", async () => {
    let resolveFn!: (value: RecoveryTracker) => void;
    getScanRecoveryTracker.mockImplementation(
      () => new Promise<RecoveryTracker>((resolve) => (resolveFn = resolve)),
    );
    renderWithClient(<RecoveryTrackerPanel scanId={7} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    resolveFn(mockTracker);
    expect(
      await screen.findByText("Record the treatments you apply and watch recovery progress"),
    ).toBeInTheDocument();
  });

  it("renders an error state with a retry button on failure", async () => {
    getScanRecoveryTracker.mockRejectedValue(new Error("network down"));
    renderWithClient(<RecoveryTrackerPanel scanId={7} />);
    expect(await screen.findByText("Couldn't load recovery tracker")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders the progress header, status and timeline on success", async () => {
    getScanRecoveryTracker.mockResolvedValue(mockTracker);
    renderWithClient(<RecoveryTrackerPanel scanId={7} />);

    expect(await screen.findByText("On Track")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "40");
    expect(screen.getByText("Neem oil spray")).toBeInTheDocument();
    expect(screen.getByText("Sprayed both sides")).toBeInTheDocument();
    // "Improving" appears both on the timeline badge and in the progress Select.
    expect(screen.getAllByText("Improving").length).toBeGreaterThan(0);
  });

  it("shows an empty timeline state when no treatments are logged", async () => {
    getScanRecoveryTracker.mockResolvedValue({ ...mockTracker, timeline: [], total_treatments: 0 });
    renderWithClient(<RecoveryTrackerPanel scanId={7} />);
    expect(await screen.findByText("No treatments recorded yet")).toBeInTheDocument();
  });
});

describe("RecoveryTrackerView interactions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getScanRecoveryTracker.mockResolvedValue(mockTracker);
    addRecoveryLog.mockResolvedValue(mockTracker.timeline[0]);
    updateRecoveryLog.mockResolvedValue(mockTracker.timeline[0]);
    deleteRecoveryLog.mockResolvedValue(undefined);
  });

  it("adds a treatment via the form", async () => {
    const user = userEvent.setup();
    renderWithClient(<RecoveryTrackerPanel scanId={7} />);
    await screen.findByText("Neem oil spray");

    await user.type(screen.getByLabelText("Treatment applied"), "Fungicide spray");
    await user.selectOptions(screen.getByLabelText("Crop response (optional)"), "improving");
    await user.type(screen.getByLabelText("Progress notes (optional)"), "Leaves look greener");
    await user.click(screen.getByRole("button", { name: "Add Treatment" }));

    await waitFor(() => expect(addRecoveryLog).toHaveBeenCalledTimes(1));
    const payload = addRecoveryLog.mock.calls[0][1] as RecoveryLogInput;
    expect(payload.treatment_applied).toBe("Fungicide spray");
    expect(payload.progress).toBe("improving");
    expect(payload.notes).toBe("Leaves look greener");
  });

  it("edits an existing log and submits the partial update", async () => {
    const user = userEvent.setup();
    renderWithClient(<RecoveryTrackerPanel scanId={7} />);
    await screen.findByText("Neem oil spray");

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const treatmentInput = screen.getByLabelText("Treatment applied");
    expect(treatmentInput).toHaveValue("Neem oil spray");

    await user.clear(treatmentInput);
    await user.type(treatmentInput, "Repeated neem oil");
    await user.click(screen.getByRole("button", { name: "Update Treatment" }));

    await waitFor(() => expect(updateRecoveryLog).toHaveBeenCalledTimes(1));
    const [, callLogId, payload] = updateRecoveryLog.mock.calls[0];
    expect(callLogId).toBe(1);
    expect((payload as RecoveryLogInput).treatment_applied).toBe("Repeated neem oil");
  });

  it("deletes a log after inline confirmation", async () => {
    const user = userEvent.setup();
    renderWithClient(<RecoveryTrackerPanel scanId={7} />);
    await screen.findByText("Neem oil spray");

    // The trash button is the confirmation trigger; the destructive confirm
    // button ("Delete") only appears after it's clicked.
    const trigger = screen.getByRole("button", { name: "Delete this treatment log?" });
    await user.click(trigger);

    const confirm = screen.getByRole("button", { name: "Delete" });
    await user.click(confirm);

    await waitFor(() => expect(deleteRecoveryLog).toHaveBeenCalledTimes(1));
    expect(deleteRecoveryLog).toHaveBeenCalledWith(7, 1);
  });

  it("cancels out of edit mode", async () => {
    const user = userEvent.setup();
    renderWithClient(<RecoveryTrackerPanel scanId={7} />);
    await screen.findByText("Neem oil spray");

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByRole("button", { name: "Update Treatment" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    // Back to add mode.
    expect(screen.getByRole("button", { name: "Add Treatment" })).toBeInTheDocument();
    const timelineItem = screen.getByText("Neem oil spray").closest("li");
    expect(timelineItem).toBeTruthy();
    expect(within(timelineItem as HTMLElement).getByText("Neem oil spray")).toBeInTheDocument();
  });
});
