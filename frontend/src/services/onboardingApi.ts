import type { OnboardingState } from "@/types";
import type { OnboardingDraftInput } from "@/schemas/onboarding.schema";
import { apiRequest } from "./apiClient";

export interface OnboardingSubmissionResult {
  status: "submitted";
  company: { id: string; name: string; tenantId: string };
  payload: OnboardingDraftInput;
}

export interface OnboardingDraftSaveResult {
  status: "saved";
  savedAt: string;
  payload: OnboardingDraftInput;
}

export const onboardingApi = {
  getState: () => apiRequest<OnboardingState>("/onboarding"),
  getDraft: () => apiRequest<OnboardingDraftInput | null>("/onboarding/draft"),
  saveDraft: (payload: OnboardingDraftInput) => apiRequest<OnboardingDraftSaveResult>("/onboarding/draft", { method: "PUT", body: JSON.stringify(payload) }),
  submit: (payload: OnboardingDraftInput) => apiRequest<OnboardingSubmissionResult>("/onboarding/submit", { method: "POST", body: JSON.stringify(payload) }),
  completeStep: (stepId: string) => apiRequest<{ stepId: string; status: string }>("/onboarding/complete-step", { method: "POST", body: JSON.stringify({ stepId }) }),
};
