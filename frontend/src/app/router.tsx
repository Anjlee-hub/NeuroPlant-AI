import { createBrowserRouter } from "react-router-dom";

import { ErrorBoundary } from "@/app/error-boundary";
import { RootLayout } from "@/components/layout/root-layout";
import { ComingSoonPage } from "@/pages/coming-soon";
import { HomePage } from "@/pages/home";
import { LoginPage } from "@/pages/login";
import { NotFoundPage } from "@/pages/not-found";
import { RegisterPage } from "@/pages/register";

/**
 * Route tree. M1 ships the shell + auth entry points; feature routes
 * (detect, doctor, marketplace) are stubs that land with their milestones.
 */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <ErrorBoundary />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
      { path: "detect", element: <ComingSoonPage navKey="detect" /> },
      { path: "doctor", element: <ComingSoonPage navKey="doctor" /> },
      { path: "marketplace", element: <ComingSoonPage navKey="marketplace" /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
