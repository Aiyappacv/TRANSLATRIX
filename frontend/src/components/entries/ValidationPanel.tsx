import { AlertTriangle, CheckCircle2, Info, RefreshCw } from "lucide-react";
import type { FinancialEntry, ValidationIssue } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function iconFor(issue: ValidationIssue) {
  return issue.severity === "info" ? Info : AlertTriangle;
}

interface ValidationPanelProps {
  entry: FinancialEntry;
  onRevalidate?: () => void;
  revalidating?: boolean;
}

export function ValidationPanel({ entry, onRevalidate, revalidating }: ValidationPanelProps) {
  const valid = entry.validationStatus === "valid" && entry.issues.length === 0;
  return (
    <Card>
      <CardHeader><CardTitle>Validation panel</CardTitle><CardDescription>Business rules, required fields, balance checks, mapping confidence, validation result, and posting readiness.</CardDescription></CardHeader>
      <CardContent className="space-y-3">
        {valid ? <div className="rounded-2xl border border-success/30 bg-success/10 p-4 text-sm text-success"><div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4" />All validation rules passed.</div></div> : entry.issues.length ? entry.issues.map((issue) => {
          const Icon = iconFor(issue);
          return (
            <div key={issue.code} className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
              <div className="flex items-start justify-between gap-3">
                <div className="flex gap-3">
                  <Icon className={issue.severity === "error" ? "h-5 w-5 text-danger" : issue.severity === "warning" ? "h-5 w-5 text-warning" : "h-5 w-5 text-primary"} />
                  <div><p className="font-semibold">{issue.code}</p><p className="mt-1 text-sm text-slate-500">{issue.message}</p>{issue.field ? <p className="mt-1 text-xs text-slate-500">Field: {issue.field}</p> : null}</div>
                </div>
                <Badge variant={issue.severity === "error" ? "danger" : issue.severity === "warning" ? "warning" : "info"}>{issue.severity}</Badge>
              </div>
            </div>
          );
        }) : <div className="rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-warning">Validation has not run against the current draft.</div>}
        <Button variant="outline" className="w-full" onClick={onRevalidate} disabled={!onRevalidate || revalidating}>
          <RefreshCw className={`h-4 w-4 ${revalidating ? "animate-spin" : ""}`} />{revalidating ? "Validating..." : "Re-run validation"}
        </Button>
      </CardContent>
    </Card>
  );
}
