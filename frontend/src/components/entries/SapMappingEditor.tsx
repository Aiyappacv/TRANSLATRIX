import { useQuery } from "@tanstack/react-query";
import { GitBranch, Sparkles } from "lucide-react";
import { sapApi } from "@/services/sapApi";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { EntryDraft } from "@/pages/entries/FinancialEntryDetailPage";

interface SapMappingEditorProps {
  draft: EntryDraft;
  onChange: (patch: Partial<EntryDraft>) => void;
}

export function SapMappingEditor({ draft, onChange }: SapMappingEditorProps) {
  const suggestion = useQuery({
    queryKey: ["sap-mapping-suggestion", draft.category, draft.subcategory],
    queryFn: () => sapApi.suggestMapping(draft.category, draft.subcategory),
    enabled: Boolean(draft.category && draft.subcategory),
  });

  const applySuggestion = () => {
    const rule = suggestion.data;
    if (!rule) return;
    onChange({
      sapTCode: rule.tCode,
      operation: rule.apiProcess,
      glAccount: rule.glAccount,
      taxCode: rule.taxCode ?? draft.taxCode,
      costCenter: rule.costCenter ?? draft.costCenter,
    });
  };

  const hasSuggestionDiff =
    suggestion.data &&
    (suggestion.data.tCode !== draft.sapTCode || suggestion.data.glAccount !== draft.glAccount || suggestion.data.apiProcess !== draft.operation);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><GitBranch className="h-5 w-5 text-primary" />SAP T-Code &amp; GL mapping</CardTitle>
        <CardDescription>Map this entry to the correct SAP transaction code, posting process, GL account, tax code, and cost center.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {suggestion.data && hasSuggestionDiff ? (
          <div className="flex flex-col gap-3 rounded-2xl border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-800 dark:border-indigo-900/60 dark:bg-indigo-950/30 dark:text-indigo-200 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-2">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                Suggested mapping for <span className="font-semibold">{draft.category} / {draft.subcategory}</span>: <Badge variant="brand">{suggestion.data.tCode}</Badge> · GL {suggestion.data.glAccount} · {suggestion.data.apiProcess}
              </p>
            </div>
            <Button size="sm" variant="outline" onClick={applySuggestion}>Apply suggestion</Button>
          </div>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="sapTCode">SAP T-Code</Label>
            <Input id="sapTCode" className="font-mono" value={draft.sapTCode} onChange={(event) => onChange({ sapTCode: event.target.value.toUpperCase() })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="operation">Posting process / API</Label>
            <Input id="operation" value={draft.operation} onChange={(event) => onChange({ operation: event.target.value })} />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="glAccount">GL account</Label>
            <Input id="glAccount" className="font-mono" value={draft.glAccount} onChange={(event) => onChange({ glAccount: event.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="costCenter">Cost center</Label>
            <Input id="costCenter" className="font-mono" value={draft.costCenter ?? ""} onChange={(event) => onChange({ costCenter: event.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="taxCode">Tax code</Label>
            <Input id="taxCode" className="font-mono" value={draft.taxCode ?? ""} onChange={(event) => onChange({ taxCode: event.target.value })} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
