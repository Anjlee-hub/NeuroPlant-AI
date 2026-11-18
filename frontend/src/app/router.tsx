
import { createBrowserRouter, Navigate } from "react-router-dom";

import { ErrorBoundary } from "@/app/error-boundary";
import {
  EntryRedirect,
  PublicOnly,
  RequireAuth,
} from "@/components/auth-route-guards";
import { RootLayout } from "@/components/layout/root-layout";

import { HomePage } from "@/pages/home";
import { LoginPage } from "@/pages/login";
import { RegisterPage } from "@/pages/register";
import { MfaSetupPage } from "@/pages/mfa-setup";
import { MfaVerifyPage } from "@/pages/mfa-verify";
import { NotFoundPage } from "@/pages/not-found";

import { ProfilePage } from "@/pages/profile";
import { OfflineQueuePage } from "@/pages/offline-queue";
import { ScanCropPage } from "@/pages/scan-crop";
import { ScanDetailPage } from "@/pages/scan-detail";
import { ScanDoctorPage } from "@/pages/scan-doctor";
import { ScanHistoryPage } from "@/pages/scan-history";
import { FarmerCalendarPage } from "@/pages/farmer-calendar";
import { AssistantPage } from "@/pages/assistant";

import { GovernmentSchemesPage } from "@/pages/government-schemes";
import { CommunityPage } from "@/pages/community";

import { MarketplaceDashboardPage } from "@/pages/marketplace-dashboard";
import { MarketplaceListingFormPage } from "@/pages/marketplace-listing-form";
import { MarketplaceBuyPage } from "@/pages/marketplace-buy";
import { MarketplaceListingDetailPage } from "@/pages/marketplace-listing-detail";
import { SellerDashboardPage } from "@/pages/seller-dashboard";
import { ProductMarketBrowsePage } from "@/pages/product-market-browse";
import { ProductMarketDetailPage } from "@/pages/product-market-detail";
import { MessagesDetailPage } from "@/pages/messages-detail";
import { MessagesListPage } from "@/pages/messages-list";
import { MarketplaceFavoritesPage } from "@/pages/marketplace-favorites";
import { MyReviewsPage } from "@/pages/my-reviews";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <EntryRedirect />,
    errorElement: <ErrorBoundary />,
  },

  // Authentication pages: no main application header or footer.
  {
    element: <PublicOnly />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        path: "/login",
        element: <LoginPage />,
      },
      {
        path: "/register",
        element: <RegisterPage />,
      },
      {
        path: "/login/mfa",
        element: <MfaVerifyPage />,
      },
    ],
  },

  // Authenticated application pages.
  {
    element: <RequireAuth />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        element: <RootLayout />,
        children: [
          {
            path: "/home",
            element: <HomePage />,
          },
          {
            path: "/settings/mfa",
            element: <MfaSetupPage />,
          },
          {
            path: "/profile",
            element: <ProfilePage />,
          },
          {
            path: "/scans",
            element: <ScanHistoryPage />,
          },
          {
            path: "/scans/:scanId",
            element: <ScanDetailPage />,
          },
          {
            path: "/scans/:scanId/doctor",
            element: <ScanDoctorPage />,
          },
          {
            path: "/offline",
            element: <OfflineQueuePage />,
          },
          {
            path: "/detect",
            element: <ScanCropPage />,
          },
          {
            path: "/doctor",
            element: <Navigate to="/scans" replace />,
          },
          {
            path: "/calendar",
            element: <FarmerCalendarPage />,
          },

          // Government schemes and farmer community.
          {
            path: "/schemes",
            element: <GovernmentSchemesPage />,
          },
          {
            path: "/community",
            element: <CommunityPage />,
          },

          // Marketplace routes.
          {
            path: "/marketplace",
            element: <MarketplaceDashboardPage />,
          },
          {
            path: "/marketplace/listings/new",
            element: <MarketplaceListingFormPage />,
          },
          {
            path: "/marketplace/listings/:listingId/edit",
            element: <MarketplaceListingFormPage />,
          },
          {
            path: "/marketplace/browse",
            element: <MarketplaceBuyPage />,
          },
          {
            path: "/marketplace/listings/:listingId",
            element: <MarketplaceListingDetailPage />,
          },
          {
            path: "/marketplace/favorites",
            element: <MarketplaceFavoritesPage />,
          },
          {
            path: "/marketplace/my-reviews",
            element: <MyReviewsPage />,
          },
          {
            path: "/marketplace/shop",
            element: <SellerDashboardPage />,
          },
          {
            path: "/marketplace/products",
            element: <ProductMarketBrowsePage />,
          },
          {
            path: "/marketplace/products/:id",
            element: <ProductMarketDetailPage />,
          },
          {
            path: "/marketplace/messages",
            element: <MessagesListPage />,
          },
          {
            path: "/marketplace/messages/:conversationId",
            element: <MessagesDetailPage />,
          },
          {
            path: "/assistant",
            element: <AssistantPage />,
          },
          {
            path: "*",
            element: <NotFoundPage />,
          },
        ],
      },
    ],
  },
]);
