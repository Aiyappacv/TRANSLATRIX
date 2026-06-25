import type { ApprovalChecklistItem } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";

interface ApprovalChecklistProps {
  items: ApprovalChecklistItem[];
  onChange: (items: ApprovalChecklistItem[]) => void;
  disabled?: boolean;
}

export function ApprovalChecklist({ items, onChange, disabled }: ApprovalChecklistProps) {
  const completed = items.filter((item) => item.checked).length;
  const requiredComplete = items.filter((item) => item.required).every((item) => item.checked);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Approval checklist</p>
          <p className="text-xs text-slate-500">Required evidence before approval or second-level routing.</p>
        </div>
        <Badge variant={requiredComplete ? "success" : "warning"}>
          {completed}/{items.length}
        </Badge>
      </div>

      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
            <Checkbox
              label={item.label}
              checked={item.checked}
              disabled={disabled}
              onChange={(event) =>
                onChange(
                  items.map((current) =>
                    current.id === item.id ? { ...current, checked: event.target.checked } : current,
                  ),
                )
              }
            />
            {item.required ? <p className="ml-7 mt-1 text-xs text-slate-500">Required</p> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
