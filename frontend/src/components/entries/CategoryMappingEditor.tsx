import { useEffect, useState } from "react";
import type { FinancialEntry, FinancialCategory } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";

const categories: FinancialCategory[] = ["Expenses", "Income", "Assets", "Liabilities"];

type EditableMapping = Pick<FinancialEntry, "category" | "subcategory" | "sapTCode" | "postingProcess" | "glSuggestion" | "accountingSoftwareAction">;

export function CategoryMappingEditor({ entry, onSave }: { entry: FinancialEntry; onSave?: (value: EditableMapping) => void | Promise<void> }) {
  const [draft, setDraft] = useState<EditableMapping>(() => ({ category: entry.category, subcategory: entry.subcategory, sapTCode: entry.sapTCode, postingProcess: entry.postingProcess, glSuggestion: entry.glSuggestion, accountingSoftwareAction: entry.accountingSoftwareAction }));
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    setDraft({ category: entry.category, subcategory: entry.subcategory, sapTCode: entry.sapTCode, postingProcess: entry.postingProcess, glSuggestion: entry.glSuggestion, accountingSoftwareAction: entry.accountingSoftwareAction });
  }, [entry]);
  const save = async () => { if (!onSave) return; setSaving(true); try { await onSave(draft); } finally { setSaving(false); } };
  return (
    <Card>
      <CardHeader><CardTitle>Category editor and SAP T-Code mapping</CardTitle><CardDescription>Editable category, subcategory, SAP T-Code, GL suggestion, and posting process.</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2"><Label>Category</Label><select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-800 dark:bg-slate-950" value={draft.category} onChange={(event) => setDraft((value) => ({ ...value, category: event.target.value as FinancialCategory }))}>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></div>
          <div className="space-y-2"><Label>Subcategory</Label><Input value={draft.subcategory} onChange={(event) => setDraft((value) => ({ ...value, subcategory: event.target.value }))} /></div>
          <div className="space-y-2"><Label>SAP T-Code</Label><Input value={draft.sapTCode} onChange={(event) => setDraft((value) => ({ ...value, sapTCode: event.target.value }))} /></div>
          <div className="space-y-2"><Label>Posting process</Label><Input value={draft.postingProcess} onChange={(event) => setDraft((value) => ({ ...value, postingProcess: event.target.value }))} /></div>
          <div className="space-y-2"><Label>GL suggestion</Label><Input value={draft.glSuggestion} onChange={(event) => setDraft((value) => ({ ...value, glSuggestion: event.target.value }))} /></div>
          <div className="space-y-2"><Label>Accounting software action</Label><Input value={draft.accountingSoftwareAction} onChange={(event) => setDraft((value) => ({ ...value, accountingSoftwareAction: event.target.value }))} /></div>
        </div>
        <div className="rounded-2xl border border-indigo-200 bg-indigo-50/50 p-4 dark:border-indigo-900/60 dark:bg-indigo-950/20">
          <div className="flex flex-wrap items-center gap-2"><Badge variant="brand">{entry.mappingSuggestion.sapTCode}</Badge><Badge variant="neutral">{entry.mappingSuggestion.postingProcess}</Badge></div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{entry.mappingSuggestion.reason}</p>
          <div className="mt-3"><ConfidenceBar label="Mapping confidence" value={entry.mappingSuggestion.confidence} compact /></div>
        </div>
        <Button className="w-full" disabled={!onSave || saving} onClick={save}>{saving ? "Saving..." : onSave ? "Save classification and mapping" : "Read-only mapping preview"}</Button>
      </CardContent>
    </Card>
  );
}
