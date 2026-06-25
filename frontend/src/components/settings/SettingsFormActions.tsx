import { RotateCcw, Save } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SettingsFormActionsProps {
  dirty: boolean;
  saving?: boolean;
  onCancel: () => void;
  onSave?: () => void;
  saveLabel?: string;
}

export function SettingsFormActions({ dirty, saving, onCancel, onSave, saveLabel = "Save changes" }: SettingsFormActionsProps) {
  return (
    <div className="sticky bottom-4 z-10 flex flex-col items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-enterprise backdrop-blur dark:border-slate-800 dark:bg-slate-950/95 sm:flex-row sm:items-center">
      <p className="text-sm text-slate-500">{dirty ? "You have unsaved changes." : "All changes are saved."}</p>
      <div className="flex gap-2">
        <Button type="button" variant="outline" disabled={!dirty || saving} onClick={onCancel}><RotateCcw className="h-4 w-4" />Cancel</Button>
        <Button type={onSave ? "button" : "submit"} disabled={!dirty || saving} onClick={onSave}><Save className="h-4 w-4" />{saving ? "Saving..." : saveLabel}</Button>
      </div>
    </div>
  );
}
