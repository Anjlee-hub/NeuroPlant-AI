import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CalendarCrop, CropCalendar, FarmerCalendar } from "@/types/calendar";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  getFarmerCalendar: vi.fn(),
  listCalendarCrops: vi.fn(),
  scheduleCrop: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({ api: apiMock }));

import { FarmerCalendarPage } from "@/pages/farmer-calendar";

function iso(offset: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offset);
  return `${d.toISOString().slice(0, 10)}T00:00:00`;
}

const today = new Date().toISOString().slice(0, 10);

const crop: CalendarCrop = {
  id: 3,
  name: "tomato",
  common_name: "Tomato",
  growth_days: 75,
  water_needs: "moderate",
  fertilizer_needs: "balanced",
  planting_start_month: 2,
  planting_end_month: 6,
  germination_days: 8,
  vegetative_days: 22,
  flowering_days: 15,
  fruiting_days: 22,
  harvest_days: 8,
  notes: null,
};

const schedule: CropCalendar = {
  schedule_id: 1,
  crop_id: 3,
  crop_name: "Tomato",
  common_name: "Tomato",
  planting_date: today,
  stages: [
    { stage: "planting", start_date: today, end_date: today },
    { stage: "germination", start_date: today, end_date: iso(7).slice(0, 10) },
    { stage: "vegetative", start_date: iso(8).slice(0, 10), end_date: iso(29).slice(0, 10) },
    { stage: "flowering", start_date: iso(30).slice(0, 10), end_date: iso(44).slice(0, 10) },
    { stage: "fruiting", start_date: iso(45).slice(0, 10), end_date: iso(66).slice(0, 10) },
    { stage: "harvest", start_date: iso(67).slice(0, 10), end_date: iso(74).slice(0, 10) },
  ],
  tasks: [
    { id: 1, schedule_id: 1, scan_id: null, kind: "watering", title: "Water the plants", due_at: iso(0), completed_at: null, snooze_count: 0, notes: null },
    { id: 2, schedule_id: 1, scan_id: null, kind: "soil_inspection", title: "Check soil pH", due_at: iso(3), completed_at: null, snooze_count: 0, notes: null },
  ],
  completed: 0,
  total: 2,
  progress: 0,
};

const dashboard: FarmerCalendar = {
  schedules: [schedule],
  today_count: 1,
  upcoming_count: 1,
  overdue_count: 0,
  completed_count: 0,
};

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/calendar", element: <FarmerCalendarPage /> },
    ],
    { initialEntries: ["/calendar"] },
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("FarmerCalendarPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMock.getFarmerCalendar.mockResolvedValue(dashboard);
    apiMock.listCalendarCrops.mockResolvedValue([crop]);
    apiMock.scheduleCrop.mockResolvedValue(schedule);
  });

  it("asks to sign in when no user is authenticated", async () => {
    authMock.user = null;
    renderPage();
    expect(await screen.findByText("Sign in to view your crop calendar.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("renders the bucket summary and each scheduled crop", async () => {
    authMock.user = { id: 1, name: "Tester" };
    renderPage();

    // The heading shows during the skeleton too — wait for real content.
    await screen.findByText("Water the plants");

    // Bucket labels render from the server counts.
    for (const bucket of ["Overdue", "Today", "Upcoming", "Completed"]) {
      expect(screen.getAllByText(bucket).length).toBeGreaterThan(0);
    }

    // The scheduled crop card appears with its stage timeline + tasks. ("Tomato"
    // shows in both the picker option and the schedule-card title.)
    expect(screen.getAllByText("Tomato").length).toBeGreaterThan(0);
    expect(screen.getByText("Check soil pH")).toBeInTheDocument();
  });

  it("shows an empty state when no schedules exist", async () => {
    authMock.user = { id: 1, name: "Tester" };
    apiMock.getFarmerCalendar.mockResolvedValue({
      ...dashboard,
      schedules: [],
      today_count: 0,
      upcoming_count: 0,
      overdue_count: 0,
      completed_count: 0,
    });
    renderPage();

    expect(await screen.findByText("No crops scheduled yet. Pick a crop above to start its calendar.")).toBeInTheDocument();
  });

  it("shows an error state with retry when the dashboard fails to load", async () => {
    authMock.user = { id: 1, name: "Tester" };
    apiMock.getFarmerCalendar.mockRejectedValue(new Error("boom"));
    renderPage();

    expect(await screen.findByText("Couldn't load your calendar")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("schedules a crop from the picker", async () => {
    authMock.user = { id: 1, name: "Tester" };
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("option", { name: "Tomato" });

    await user.selectOptions(screen.getByLabelText("Crop"), "3");
    await user.click(screen.getByRole("button", { name: "Schedule" }));

    await waitFor(() => expect(apiMock.scheduleCrop).toHaveBeenCalledTimes(1));
    expect(apiMock.scheduleCrop).toHaveBeenCalledWith(3, {});
  });
});
