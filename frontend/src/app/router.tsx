import { createBrowserRouter, Navigate } from "react-router-dom";
import Maps from "@/pages/maps";
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
import { MarketplaceBuyPage } from "@/pages/marketplace-buy";
import { MarketplaceListingDetailPage } from "@/pages/marketplace-listing-detail";
import { SellerDashboardPage } from "@/pages/seller-dashboard";
import { ProductMarketBrowsePage } from "@/pages/product-market-browse";
import { ProductMarketDetailPage } from "@/pages/product-market-detail";
import { MessagesDetailPage } from "@/pages/messages-detail";
import { MessagesListPage } from "@/pages/messages-list";
import { MarketplaceFavoritesPage } from "@/pages/marketplace-favorites";
import { MyReviewsPage } from "@/pages/my-reviews";

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
      // Buyer storefront (M4 T3): browse with server-side filters + the shared
      // listing detail. Static segments (new/edit) outrank :listingId, so the
      // farmer's create/edit routes stay unambiguous.
      { path: "marketplace/browse", element: <MarketplaceBuyPage /> },
      { path: "marketplace/listings/:listingId", element: <MarketplaceListingDetailPage /> },
      // Marketplace trust (M4 Task 6): saved items + the caller's reviews.
      { path: "marketplace/favorites", element: <MarketplaceFavoritesPage /> },
      { path: "marketplace/my-reviews", element: <MyReviewsPage /> },
      // Seller Portal (M4 T4): seller dashboard at /marketplace/shop, public
      // product market at /marketplace/products (browse + detail). Static segments
      // rank above :id, so "products" won't capture "products/new" etc. — we
      // don't have such routes yet, but this keeps future-proof.
      { path: "marketplace/shop", element: <SellerDashboardPage /> },
      { path: "marketplace/products", element: <ProductMarketBrowsePage /> },
      { path: "marketplace/products/:id", element: <ProductMarketDetailPage /> },
      // Buyer↔seller messaging (M4 T5): inbox + one thread.
      { path: "marketplace/messages", element: <MessagesListPage /> },
      { path: "marketplace/messages/:conversationId", element: <MessagesDetailPage /> },
      // Voice AI assistant is live (M3 T6): text or voice question, spoken replies.
      { path: "assistant", element: <AssistantPage /> },
      { path: "maps", element: <Maps /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
