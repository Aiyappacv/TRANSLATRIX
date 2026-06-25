import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import type { Permission } from "@/utils/permissions";

interface ProtectedRouteProps {
  requiredPermissions?: Permission[];
}

export function ProtectedRoute({ requiredPermissions }: ProtectedRouteProps) {
  const location = useLocation();
  const { user, accessToken } = useAuthStore();

  if (!user || !accessToken) {
    return <Navigate to="/auth/login" replace state={{ from: location.pathname }} />;
  }

  const allowed = !requiredPermissions?.length || requiredPermissions.some((permission) => user.permissions.includes(permission));
  if (!allowed) {
    return <Navigate to="/app/forbidden" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
