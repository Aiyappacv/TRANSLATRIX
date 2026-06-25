import { useAuthStore } from "@/store/authStore";
import type { Permission } from "@/utils/permissions";

export function usePermissions() {
  const user = useAuthStore((state) => state.user);
  const hasPermission = (permission?: Permission) => !permission || Boolean(user?.permissions.includes(permission));
  const hasAnyPermission = (required?: Permission[]) => !required?.length || required.some((permission) => user?.permissions.includes(permission));
  return { hasPermission, hasAnyPermission, permissions: user?.permissions ?? [] };
}
