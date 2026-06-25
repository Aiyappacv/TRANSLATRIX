import { useMutation } from "@tanstack/react-query";
import { authApi } from "@/services/authApi";
import { useAuthStore } from "@/store/authStore";
import { useTenantStore } from "@/store/tenantStore";
import type { LoginInput } from "@/schemas/auth.schema";
import { isAuthSession, type AuthSession } from "@/types";

export function useAuth() {
  const { user, accessToken, setSession, clearSession } = useAuthStore();
  const activateUserCompany = useTenantStore((state) => state.activateUserCompany);
  const clearTenant = useTenantStore((state) => state.clearTenant);

  const activateSession = (session: AuthSession) => {
    setSession(session);
    activateUserCompany({ id: session.user.companyId, name: session.user.companyName, tenantId: session.user.tenantId });
  };

  const loginMutation = useMutation({
    mutationFn: (input: LoginInput) => authApi.login(input),
    onSuccess: (result) => {
      if (isAuthSession(result)) activateSession(result);
    },
  });

  const verifyMfaMutation = useMutation({
    mutationFn: (input: { challengeToken: string; code: string }) => authApi.verifyMfa(input),
    onSuccess: activateSession,
  });

  return {
    user,
    accessToken,
    isAuthenticated: Boolean(user && accessToken),
    login: loginMutation.mutateAsync,
    loginStatus: loginMutation.status,
    verifyMfa: verifyMfaMutation.mutateAsync,
    verifyMfaStatus: verifyMfaMutation.status,
    logout: () => {
      clearSession();
      clearTenant();
    },
  };
}
