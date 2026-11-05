import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import type {
  EligibilityCheck,
  GovernmentScheme,
  GovernmentSchemePage,
} from "@/types/scheme";

const authMock = vi.hoisted(() => ({
  user: null as { id: number; name: string } | null,
}));
const apiMock = vi.hoisted(() => ({
  listGovernmentSchemes: vi.fn(),
  getGovernmentScheme: vi.fn(),
  checkSchemeEligibility: vi.fn(),
}));

vi.mock("@/stores/auth", () => ({
  useAuth: () => ({ user: authMock.user, loading: false }),
}));
vi.mock("@/lib/api", () => ({
  api: apiMock,
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
}));

import { GovernmentSchemesPage } from "@/pages/government-schemes";

const scheme: GovernmentScheme = {
  id: 7,
  name: "Verified irrigation support",
  category: "irrigation",
  description: "Published scheme description.",
  benefits: "Published benefits.",
  state_codes: ["KA"],
  crops: ["rice"],
  farmer_categories: ["small"],
  eligibility_requirements: ["Meet the published rules."],
  required_documents: ["Identity proof"],
  application_instructions: "Use the official portal.",
  official_application_url: "https://example.gov/apply",
  subsidy_details: "Details from the source.",
  source_name: "Official test source",
  source_url: "https://example.gov/scheme",
  last_verified_at: "2026-10-01T00:00:00Z",
  is_verified: true,
};

const page: GovernmentSchemePage = {
  items: [scheme],
  total: 1,
  page: 1,
  page_size: 20,
  pages: 1,
  source_status: "scheme_records_available",
  source_note: "Records are curated from attributed sources.",
};

function renderPage() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <div>home</div> },
      { path: "/login", element: <div>login</div> },
      { path: "/schemes", element: <GovernmentSchemesPage /> },
    ],
    { initialEntries: ["/schemes"] },
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("GovernmentSchemesPage", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    vi.clearAllMocks();
    authMock.user = { id: 1, name: "Farmer" };
    apiMock.listGovernmentSchemes.mockResolvedValue(page);
    apiMock.getGovernmentScheme.mockResolvedValue(scheme);
    apiMock.checkSchemeEligibility.mockResolvedValue({
      scheme_id: scheme.id,
      outcome: "potentially_eligible",
      matched_rules: ["state_code matches the published rule"],
      unmet_rules: [],
      explanation: "Confirm with the official authority.",
      legal_determination: false,
    } satisfies EligibilityCheck);
  });

  it("requires authentication and links to sign in", async () => {
    authMock.user = null;
    renderPage();

    expect(await screen.findByText("Sign in to browse government schemes")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login",
    );
    expect(apiMock.listGovernmentSchemes).not.toHaveBeenCalled();
  });

  it("shows the backend empty state without displaying fabricated schemes", async () => {
    apiMock.listGovernmentSchemes.mockResolvedValue({
      ...page,
      items: [],
      total: 0,
      pages: 0,
      source_status: "no_scheme_records",
      source_note: "No government scheme records are loaded.",
    });
    renderPage();

    expect(await screen.findByText("No scheme records are available")).toBeInTheDocument();
    expect(screen.queryByText(scheme.name)).not.toBeInTheDocument();
    expect(screen.getByText("No government scheme records are loaded.")).toBeInTheDocument();
  });

  it("filters with supported fields, shows source details, and renders actual eligibility results", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText(scheme.name)).toBeInTheDocument();
    await user.type(screen.getByLabelText("State code"), "KA");
    await user.type(screen.getByLabelText("Crop"), "rice");
    await user.type(screen.getByLabelText("Farmer category"), "small");
    await user.type(screen.getByLabelText("Scheme category"), "irrigation");

    await waitFor(() => {
      expect(apiMock.listGovernmentSchemes).toHaveBeenLastCalledWith({
        state_code: "KA",
        crop_name: "rice",
        farmer_category: "small",
        category: "irrigation",
        page: 1,
        page_size: 20,
      });
    });

    await user.click(screen.getByRole("button", { name: "Details & check eligibility" }));
    expect(await screen.findByText("Official test source")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /https:\/\/example.gov\/scheme/ })).toHaveAttribute(
      "href",
      "https://example.gov/scheme",
    );
    expect(screen.getByRole("link", { name: "Open official application page" })).toHaveAttribute(
      "href",
      "https://example.gov/apply",
    );

    await user.click(screen.getByRole("button", { name: "Check eligibility" }));
    expect(await screen.findByText("Potentially eligible")).toBeInTheDocument();
    expect(screen.getByText(/not a legal determination or guarantee/i)).toBeInTheDocument();
    expect(apiMock.checkSchemeEligibility).toHaveBeenLastCalledWith(7, {
      state_code: "KA",
      crop_name: "rice",
      farmer_category: "small",
    });

    apiMock.checkSchemeEligibility.mockResolvedValueOnce({
      scheme_id: scheme.id,
      outcome: "not_eligible",
      matched_rules: [],
      unmet_rules: ["state_code does not match the published rule"],
      explanation: "One or more details do not match.",
      legal_determination: false,
    });
    await user.click(screen.getByRole("button", { name: "Check eligibility" }));
    expect(
      await screen.findByText("Not eligible under the provided details"),
    ).toBeInTheDocument();
  });

  it("renders unknown eligibility results", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(scheme.name);
    await user.click(screen.getByRole("button", { name: "Details & check eligibility" }));
    await screen.findByText("Official test source");

    apiMock.checkSchemeEligibility.mockResolvedValueOnce({
      scheme_id: scheme.id,
      outcome: "unknown",
      matched_rules: [],
      unmet_rules: ["crop_name was not provided"],
      explanation: "The available structured rules are insufficient.",
      legal_determination: false,
    });
    await user.click(screen.getByRole("button", { name: "Check eligibility" }));
    expect(await screen.findByText("Unable to determine")).toBeInTheDocument();
  });

  it("shows a list error with a working retry action", async () => {
    const user = userEvent.setup();
    apiMock.listGovernmentSchemes
      .mockRejectedValueOnce(new Error("Service unavailable"))
      .mockResolvedValueOnce(page);
    renderPage();

    expect(await screen.findByText("Couldn't load government schemes")).toBeInTheDocument();
    expect(screen.getByText("Service unavailable")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText(scheme.name)).toBeInTheDocument();
  });
});
