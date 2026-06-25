import type { Permission } from "@/utils/permissions";
import { usePermissions } from "@/hooks/usePermissions";

export function Can({ permissions, children, fallback = null }: { permissions?: Permission[]; children: React.ReactNode; fallback?: React.ReactNode }) {
  const { hasAnyPermission } = usePermissions();
  return hasAnyPermission(permissions) ? <>{children}</> : <>{fallback}</>;
}
