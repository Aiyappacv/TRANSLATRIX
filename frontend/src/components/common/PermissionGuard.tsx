import type { Permission } from "@/utils/permissions";
import { usePermissions } from "@/hooks/usePermissions";
import { Alert } from "@/components/ui/alert";

export function PermissionGuard({ permissions, children }: { permissions?: Permission[]; children: React.ReactNode }) {
  const { hasAnyPermission } = usePermissions();
  if (!hasAnyPermission(permissions)) return <Alert tone="danger">You do not have permission to view this section.</Alert>;
  return <>{children}</>;
}
