import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { bucketTask, ScheduleCard } from "@/components/calendar/schedule-card";
import { api } from "@/lib/api";
import type { CalendarTask, CropCalendar } from "@/types/calendar";

vi.mock("@/lib/api", () => ({
  api: {
    updateCalendarTask: vi.fn(),
    deleteCalendarTask: vi.fn(),
    addCalendarTask: vi.fn(),
  },
}));

const updateCalendarTask = api.updateCalendarTask as ReturnType<typeof vi.fn>;
const deleteCalendarTask = api.deleteCalendarTask as ReturnType<typeof vi.fn>;
const addCalendarTask = api.addCalendarTask as ReturnType<typeof vi.fn>;

/** UTC date `offset` days from today, formatted the way the API returns dates. */
function iso(offset: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offset);
  return `${d.toISOString().slice(0, 10)}T00:00:00`;
}

const today = new Date().toISOString().slice(0, 10);

/** A schedule with one task per bucket, so group labels + actions are testable. */
function makeSchedule(overrides: Partial<CropCalendar> = {}): CropCalendar {
  return {
    schedule_id: 1,
    crop_id: 3,
    crop_name: "Tomato",
    common_name: "Tomato",
    planting_date: iso(-10).slice(0, 10),
    stages: [
      { stage: "planting", start_date: today, end_date: today },
      { stage: "germination", start_date: today, end_date: iso(7).slice(0, 10) },
      { stage: "vegetative", start_date: iso(8).slice(0, 10), end_date: iso(29).slice(0, 10) },
      { stage: "flowering", start_date: iso(30).slice(0, 10), end_date: iso(44).slice(0, 10) },
      { stage: "fruiting", start_date: iso(45).slice(0, 10), end_date: iso(66).slice(0, 10) },
      { stage: "harvest", start_date: iso(67).slice(0, 10), end_date: iso(74).slice(0, 10) },
    ],
    tasks: [
      { id: 1, schedule_id: 1, scan_id: null, kind: "watering", title: "Water the plants", due_at: iso(-1), completed_at: null, snooze_count: 0, notes: null },
      { id: 2, schedule_id: 1, scan_id: null, kind: "fertilizer", title: "Apply compost tea", due_at: iso(0), completed_at: null, snooze_count: 0, notes: null },
      { id: 3, schedule_id: 1, scan_id: null, kind: "soil_inspection", title: "Check soil pH", due_at: iso(2), completed_at: null, snooze_count: 0, notes: "Record pH level" },
      { id: 4, schedule_id: 1, scan_id: null, kind: "custom", title: "Mulch rows", due_at: iso(-5), completed_at: "2026-08-01T09:00:00", snooze_count: 0, notes: null },
    ],
    completed: 1,
    total: 4,
    progress: 0.25,
    ...overrides,
  };
}

function renderCard(schedule: CropCalendar) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ScheduleCard schedule={schedule} today={today} />
    </QueryClientProvider>,
  );
}

function taskRow(title: string): HTMLElement {
  const row = screen.getByText(title).closest("li");
  if (!row) throw new Error(`no row for ${title}`);
  return row;
}

describe("bucketTask", () => {
  const task = (due: string, completed: string | null = null): CalendarTask => ({
    id: 1,
    schedule_id: 1,
    scan_id: null,
    kind: "watering",
    title: "t",
    due_at: due,
    completed_at: completed,
    snooze_count: 0,
    notes: null,
  });

  it("buckets by completion first, then today / overdue / upcoming", () => {
    const completed = task(iso(-10), "2026-08-01T09:00:00");
    const todayTask = task(`${today}T00:00:00`);
    const overdue = task(iso(-1));
    const upcoming = task(iso(2));
    expect(bucketTask(completed, today)).toBe("completed");
    expect(bucketTask(todayTask, today)).toBe("today");
    expect(bucketTask(overdue, today)).toBe("overdue");
    expect(bucketTask(upcoming, today)).toBe("upcoming");
  });
});

describe("ScheduleCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the crop name, progress bar and stage timeline", () => {
    renderCard(makeSchedule());

    expect(screen.getByText("Tomato")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "25");
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText("1 of 4 tasks done")).toBeInTheDocument();

    for (const stage of ["Planting", "Germination", "Vegetative", "Flowering", "Fruiting", "Harvest"]) {
      expect(screen.getByText(stage)).toBeInTheDocument();
    }
  });

  it("groups tasks into the four buckets with counts", () => {
    renderCard(makeSchedule());
    expect(screen.getByText("Overdue (1)")).toBeInTheDocument();
    expect(screen.getByText("Today (1)")).toBeInTheDocument();
    expect(screen.getByText("Upcoming (1)")).toBeInTheDocument();
    expect(screen.getByText("Completed (1)")).toBeInTheDocument();
  });

  it("shows an empty state when a schedule has no tasks", () => {
    renderCard(makeSchedule({ tasks: [], completed: 0, total: 0, progress: 0 }));
    expect(screen.getByText("No tasks in this schedule yet.")).toBeInTheDocument();
  });

  it("completes a task via the round check button", async () => {
    const user = userEvent.setup();
    updateCalendarTask.mockResolvedValue(makeSchedule().tasks[0]);
    renderCard(makeSchedule());

    await user.click(
      within(taskRow("Apply compost tea")).getByRole("button", { name: "Mark as complete" }),
    );

    await waitFor(() => expect(updateCalendarTask).toHaveBeenCalledTimes(1));
    expect(updateCalendarTask).toHaveBeenCalledWith(2, { completed: true });
  });

  it("snoozes a task by one day", async () => {
    const user = userEvent.setup();
    updateCalendarTask.mockResolvedValue(makeSchedule().tasks[0]);
    renderCard(makeSchedule());

    await user.click(
      within(taskRow("Water the plants")).getByRole("button", { name: "Snooze 1 day" }),
    );

    await waitFor(() => expect(updateCalendarTask).toHaveBeenCalledTimes(1));
    expect(updateCalendarTask).toHaveBeenCalledWith(1, { snooze_days: 1 });
  });

  it("deletes a task only after inline confirmation", async () => {
    const user = userEvent.setup();
    deleteCalendarTask.mockResolvedValue(undefined);
    renderCard(makeSchedule());

    const row = taskRow("Water the plants");
    expect(within(row).queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();

    await user.click(within(row).getByRole("button", { name: "Delete task" }));
    await user.click(within(row).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(deleteCalendarTask).toHaveBeenCalledTimes(1));
    expect(deleteCalendarTask).toHaveBeenCalledWith(1);
  });

  it("adds a custom note / to-do", async () => {
    const user = userEvent.setup();
    addCalendarTask.mockResolvedValue(makeSchedule().tasks[0]);
    renderCard(makeSchedule());

    await user.click(screen.getByRole("button", { name: "Add a custom note / to-do" }));
    await user.type(screen.getByLabelText("What needs doing?"), "Check drip lines");
    await user.click(screen.getByRole("button", { name: "Add task" }));

    await waitFor(() => expect(addCalendarTask).toHaveBeenCalledTimes(1));
    expect(addCalendarTask).toHaveBeenCalledWith({
      schedule_id: 1,
      title: "Check drip lines",
      due_at: null,
    });
  });
});
