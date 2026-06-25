import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import type { Permission } from "@/utils/permissions";
import type { RoleCode } from "@/types";

interface AccessRouteProps {
  children: ReactNode;
  permissions?: Permission[];
  roles?: RoleCode[];
  requireAllPermissions?: boolean;
}

export function AccessRoute({ children, permissions, roles, requireAllPermissions = false }: AccessRouteProps) {
  const location = useLocation();
  const user = useAuthStore((state) => state.user);

  if (!user) {
    return <Navigate to="/auth/login" replace state={{ from: location.pathname + location.search }} />;
  }

  const permissionAllowed = !permissions?.length
    || (requireAllPermissions
      ? permissions.every((permission) => user.permissions.includes(permission))
      : permissions.some((permission) => user.permissions.includes(permission)));
  const roleAllowed = !roles?.length || roles.some((role) => user.roles.includes(role));

  if (!permissionAllowed || !roleAllowed) {
    return <Navigate to="/app/forbidden" replace state={{ from: location.pathname + location.search }} />;
  }

  return <>{children}</>;
}
