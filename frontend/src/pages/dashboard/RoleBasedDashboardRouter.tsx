import { useEffect } from "react";
import { Navigate, useParams } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { dashboardPathRoles, dashboardRolePaths, getDashboardRole } from "@/utils/dashboardRoles";
import { RoleDashboardPage } from "./RoleDashboardPage";

export { dashboardRolePaths, getDashboardRole } from "@/utils/dashboardRoles";

export function RoleBasedDashboardRouter() {
  const { dashboardRole } = useParams();
  const user = useAuthStore((state) => state.user);
  const activeRole = useAuthStore((state) => state.activeRole);
  const setActiveRole = useAuthStore((state) => state.setActiveRole);

  const selected = dashboardRole ? dashboardPathRoles[dashboardRole] : undefined;
  const role = user
    ? selected && user.roles.includes(selected)
      ? selected
      : getDashboardRole(user.roles, activeRole)
    : "read_only";
  const expectedPath = dashboardRolePaths[role] ?? "read-only";

  useEffect(() => {
    if (user && role !== activeRole) setActiveRole(role);
  }, [activeRole, role, setActiveRole, user]);

  if (!user) return <Navigate to="/auth/login" replace />;
  if (user.roles.includes("spectra_super_admin") && user.roles.length === 1) {
    return <Navigate to="/super-admin/dashboard" replace />;
  }
  if (!dashboardRole || dashboardRole !== expectedPath) {
    return <Navigate to={`/app/dashboard/${expectedPath}`} replace />;
  }
  return <RoleDashboardPage role={role} />;
}
