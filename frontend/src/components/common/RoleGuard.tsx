import type { RoleCode } from "@/types";
import { useAuthStore } from "@/store/authStore";
import { Alert } from "@/components/ui/alert";

export function RoleGuard({ roles, children }: { roles: RoleCode[]; children: React.ReactNode }) {
  const user = useAuthStore((state) => state.user);
  if (!user?.roles.some((role) => roles.includes(role))) return <Alert tone="danger">This action is restricted for your role.</Alert>;
  return <>{children}</>;
}
