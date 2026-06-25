export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  status: "completed" | "current" | "pending";
}

export interface OnboardingState {
  currentStep: string;
  completion: number;
  steps: OnboardingStep[];
}
