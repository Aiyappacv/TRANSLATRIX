import type { AuthSession, LoginResult } from "@/types";
import type { LoginInput } from "@/schemas/auth.schema";
import { apiRequest } from "./apiClient";

export const authApi = {
  login: (input: LoginInput) => apiRequest<LoginResult>("/auth/login", { method: "POST", body: JSON.stringify(input) }),
  verifyMfa: (payload: { challengeToken: string; code: string }) => apiRequest<AuthSession>("/auth/mfa/verify", { method: "POST", body: JSON.stringify(payload) }),
  me: () => apiRequest<AuthSession["user"]>("/auth/me"),
  forgotPassword: (email: string) => apiRequest<{ status: string }>("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }),
  resetPassword: (payload: { token: string; password: string }) => apiRequest<{ status: string }>("/auth/reset-password", { method: "POST", body: JSON.stringify(payload) }),
};
