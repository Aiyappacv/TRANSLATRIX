import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ProgressStepper } from "./ProgressStepper";

interface MultiStepWizardProps {
  steps: string[];
  currentIndex: number;
  renderStep: (index: number) => ReactNode;
  onBack: () => void;
  onNext: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  busy?: boolean;
}

export function MultiStepWizard({ steps, currentIndex, renderStep, onBack, onNext, nextLabel, nextDisabled, busy }: MultiStepWizardProps) {
  return (
    <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
      <ProgressStepper steps={steps} currentIndex={currentIndex} />
      <div className="space-y-6">
        {renderStep(currentIndex)}
        <div className="flex justify-between">
          <Button type="button" variant="outline" disabled={currentIndex === 0 || busy} onClick={onBack}>Back</Button>
          <Button type="button" disabled={nextDisabled || busy} onClick={onNext}>{busy ? "Saving..." : nextLabel ?? (currentIndex === steps.length - 1 ? "Submit" : "Next")}</Button>
        </div>
      </div>
    </div>
  );
}
