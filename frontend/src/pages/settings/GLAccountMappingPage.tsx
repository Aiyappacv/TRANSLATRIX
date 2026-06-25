import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { GlAccountMapping } from "@/types";
import { settingsApi } from "@/services/settingsApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges";
import { useToast } from "@/hooks/useToast";
import { SettingsFormActions } from "@/components/settings/SettingsFormActions";

export function GLAccountMappingPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["settings", "gl-account-mapping"], queryFn: settingsApi.getGlMappings });
  const [rows, setRows] = useState<GlAccountMapping[]>([]);
  useEffect(() => { if (query.data) setRows(structuredClone(query.data)); }, [query.data]);
  const dirty = useMemo(() => JSON.stringify(rows) !== JSON.stringify(query.data ?? []), [query.data, rows]);
  useUnsavedChanges(dirty);
  const save = useMutation({ mutationFn: settingsApi.saveGlMappings, onSuccess: (data) => { setRows(data); queryClient.setQueryData(["settings", "gl-account-mapping"], data); toast.success("GL mappings saved"); }, onError: (error) => toast.error("Unable to save GL mappings", error instanceof Error ? error.message : "Unexpected error") });
  if (query.isLoading) return <LoadingState label="Loading GL account mappings..." />;
  if (query.isError) return <ErrorState title="GL mappings unavailable" description="GL mapping rules could not be loaded." onRetry={() => query.refetch()} />;
  const update = (index: number, patch: Partial<GlAccountMapping>) => setRows((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row));
  return <div className="space-y-6"><PageHeader eyebrow="Phase 12 · Administration" title="GL account mapping" description="Category and keyword rules mapped to GL account, cost center, tax code, and priority." actions={<Button onClick={() => setRows((current) => [...current, { id: `gl-${Date.now()}`, category: "Expenses", subcategory: "New rule", keywords: [], glAccount: "610000", costCenterDefault: "", taxCodeDefault: "", priority: 100, active: true }])}>Add GL rule</Button>} />
    <Card><CardContent className="overflow-x-auto p-0"><table className="w-full min-w-[1050px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900"><tr>{["Category", "Subcategory", "Keyword rules", "GL account", "Cost center default", "Tax code default", "Priority", "Status"].map((header) => <th key={header} className="border-b border-slate-200 px-3 py-3 dark:border-slate-800">{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800"><td className="p-2"><Input value={row.category} onChange={(event) => update(index, { category: event.target.value })} /></td><td className="p-2"><Input value={row.subcategory} onChange={(event) => update(index, { subcategory: event.target.value })} /></td><td className="p-2"><Input value={row.keywords.join(", ")} onChange={(event) => update(index, { keywords: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></td><td className="p-2"><Input className="font-mono" value={row.glAccount} onChange={(event) => update(index, { glAccount: event.target.value })} /></td><td className="p-2"><Input value={row.costCenterDefault ?? ""} onChange={(event) => update(index, { costCenterDefault: event.target.value })} /></td><td className="p-2"><Input value={row.taxCodeDefault ?? ""} onChange={(event) => update(index, { taxCodeDefault: event.target.value })} /></td><td className="p-2"><Input type="number" value={row.priority} onChange={(event) => update(index, { priority: Number(event.target.value) })} /></td><td className="p-2"><div className="flex items-center gap-2"><Switch checked={row.active} onChange={(event) => update(index, { active: event.target.checked })} /><Badge variant={row.active ? "success" : "neutral"}>{row.active ? "Active" : "Inactive"}</Badge></div></td></tr>)}</tbody></table></CardContent></Card>
    <SettingsFormActions dirty={dirty} saving={save.isPending} onCancel={() => setRows(structuredClone(query.data ?? []))} onSave={() => save.mutate(rows)} saveLabel="Save GL mappings" />
  </div>;
}
