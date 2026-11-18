import { Navigate } from "react-router-dom";
import { useAuth } from "@/stores/auth";

interface AdminRouteProps {
  children: React.ReactNode;
}

export function AdminRoute({ children }: AdminRouteProps) {
  const user = useAuth((state) => state.user);
  const hydrated = useAuth((state) => state.hydrated);

  if (!hydrated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        Loading account...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
