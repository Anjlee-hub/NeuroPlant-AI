
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/stores/auth";

function AuthLoadingScreen() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-3">
        <div className="size-9 animate-spin rounded-full border-4 border-primary/20 border-t-primary" />
        <p className="text-sm text-muted-foreground">
          Restoring your session...
        </p>
      </div>
    </main>
  );
}

/** Redirects the root URL according to the current authentication state. */
export function EntryRedirect() {
  const hydrated = useAuth((state) => state.hydrated);
  const user = useAuth((state) => state.user);

  if (!hydrated) return <AuthLoadingScreen />;

  return (
    <Navigate to={user ? "/home" : "/login"} replace />
  );
}

/** Login and registration are only available to logged-out visitors. */
export function PublicOnly() {
  const hydrated = useAuth((state) => state.hydrated);
  const user = useAuth((state) => state.user);
  

  if (!hydrated) return <AuthLoadingScreen />;

  if (user) {
    return <Navigate to="/home" replace />;
  }

  // Allow the MFA route to remain accessible without an authenticated user.
  return <Outlet />;
}

/** All application pages require an authenticated session. */
export function RequireAuth() {
  const hydrated = useAuth((state) => state.hydrated);
  const user = useAuth((state) => state.user);
  const location = useLocation();

  if (!hydrated) return <AuthLoadingScreen />;

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return <Outlet />;
}
