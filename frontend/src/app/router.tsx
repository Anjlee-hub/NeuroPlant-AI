import { createBrowserRouter, Navigate } from "react-router-dom";

import { ErrorBoundary } from "@/app/error-boundary";
import { RootLayout } from "@/components/layout/root-layout";
import { HomePage } from "@/pages/home";
import { LoginPage } from "@/pages/login";
import { MfaSetupPage } from "@/pages/mfa-setup";
import { MfaVerifyPage } from "@/pages/mfa-verify";
import { NotFoundPage } from "@/pages/not-found";
import { OfflineQueuePage } from "@/pages/offline-queue";
import { ProfilePage } from "@/pages/profile";
import { RegisterPage } from "@/pages/register";
import { ScanCropPage } from "@/pages/scan-crop";
import { ScanDetailPage } from "@/pages/scan-detail";
import { ScanDoctorPage } from "@/pages/scan-doctor";
import { ScanHistoryPage } from "@/pages/scan-history";
import { FarmerCalendarPage } from "@/pages/farmer-calendar";
import { AssistantPage } from "@/pages/assistant";
import { MarketplaceDashboardPage } from "@/pages/marketplace-dashboard";
import { MarketplaceListingFormPage } from "@/pages/marketplace-listing-form";

/**
 * Route tree. Every nav destination resolves to a live page or an honest
 * "planned for Milestone X" page — there are no dead links (M2.1).
 */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <ErrorBoundary />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "login", element: <LoginPage /> },
      { path: "login/mfa", element: <MfaVerifyPage /> },
      { path: "register", element: <RegisterPage /> },
      { path: "settings/mfa", element: <MfaSetupPage /> },
      { path: "profile", element: <ProfilePage /> },
      { path: "scans", element: <ScanHistoryPage /> },
      { path: "scans/:scanId", element: <ScanDetailPage /> },
      { path: "scans/:scanId/doctor", element: <ScanDoctorPage /> },
      { path: "offline", element: <OfflineQueuePage /> },
      { path: "detect", element: <ScanCropPage /> },
      // Crop Doctor is live per-scan (M3 T4): the nav hub lands on the scan
      // list so the user picks a scan to open its dashboard.
      { path: "doctor", element: <Navigate to="/scans" replace /> },
      { path: "calendar", element: <FarmerCalendarPage /> },
      // Farmer Crop Listings (M4 T2): dashboard + create/edit surface. The
      // create route is declared before the edit route for clarity, though
      // React Router ranks static segments above `:id` automatically.
      { path: "marketplace", element: <MarketplaceDashboardPage /> },
      { path: "marketplace/listings/new", element: <MarketplaceListingFormPage /> },
      { path: "marketplace/listings/:listingId/edit", element: <MarketplaceListingFormPage /> },
      // Voice AI assistant is live (M3 T6): text or voice question, spoken replies.
      { path: "assistant", element: <AssistantPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
