import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { SapMappingRule } from "@/types";
import { settingsApi } from "@/services/settingsApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { SettingsFormActions } from "@/components/settings/SettingsFormActions";
import { useUnsavedChanges } from "@/hooks/useUnsavedChanges";
import { useToast } from "@/hooks/useToast";

export function SapTCodeMappingPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["settings", "sap-tcode-mapping"], queryFn: settingsApi.getMappings });
  const [rows, setRows] = useState<SapMappingRule[]>([]);
  useEffect(() => { if (query.data) setRows(structuredClone(query.data)); }, [query.data]);
  const dirty = useMemo(() => JSON.stringify(rows) !== JSON.stringify(query.data ?? []), [query.data, rows]);
  useUnsavedChanges(dirty);
  const save = useMutation({ mutationFn: settingsApi.saveMappings, onSuccess: (data) => { setRows(data); queryClient.setQueryData(["settings", "sap-tcode-mapping"], data); toast.success("SAP T-Code mappings saved", "New entries will use the updated mapping priorities."); }, onError: (error) => toast.error("Unable to save mappings", error instanceof Error ? error.message : "Unexpected error") });
  if (query.isLoading) return <LoadingState label="Loading SAP T-Code mappings..." />;
  if (query.isError) return <ErrorState title="SAP mapping unavailable" description="Mapping rules could not be loaded." onRetry={() => query.refetch()} />;
  const update = (index: number, patch: Partial<SapMappingRule>) => setRows((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row));
  const add = () => setRows((current) => [...current, { id: `mapping-${Date.now()}`, category: "Expenses", subcategory: "New rule", keywords: [], tCode: "FB50", apiProcess: "Journal Entry", sapApi: "API_JOURNAL_ENTRY_SRV", documentType: "SA", glAccount: "610000", requiresVendor: false, requiresCustomer: false, requiresAsset: false, requiresCostCenter: true, approvalRequired: true, priority: 100, active: true }]);
  return <div className="space-y-6">
    <PageHeader eyebrow="Phase 12 · Administration" title="SAP T-Code mapping" description="Editable category, keyword, T-Code, SAP process/API, document type, master-data requirements, and activation rules." actions={<Button onClick={add}>Add mapping rule</Button>} />
    <Card><CardContent className="overflow-x-auto p-0"><table className="w-full min-w-[1500px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900"><tr>{["Category", "Subcategory", "Keywords", "T-Code", "SAP process", "SAP API", "Doc type", "GL account", "Vendor", "Customer", "Asset", "Cost center", "Priority", "Status"].map((header) => <th key={header} className="border-b border-slate-200 px-3 py-3 dark:border-slate-800">{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800"><td className="p-2"><Input value={row.category} onChange={(event) => update(index, { category: event.target.value })} /></td><td className="p-2"><Input value={row.subcategory} onChange={(event) => update(index, { subcategory: event.target.value })} /></td><td className="p-2"><Input value={row.keywords.join(", ")} onChange={(event) => update(index, { keywords: event.target.value.split(",").map((value) => value.trim()).filter(Boolean) })} /></td><td className="p-2"><Input className="font-mono" value={row.tCode} onChange={(event) => update(index, { tCode: event.target.value.toUpperCase() })} /></td><td className="p-2"><Input value={row.apiProcess} onChange={(event) => update(index, { apiProcess: event.target.value })} /></td><td className="p-2"><Input className="font-mono" value={row.sapApi ?? ""} onChange={(event) => update(index, { sapApi: event.target.value })} /></td><td className="p-2"><Input value={row.documentType} onChange={(event) => update(index, { documentType: event.target.value })} /></td><td className="p-2"><Input className="font-mono" value={row.glAccount} onChange={(event) => update(index, { glAccount: event.target.value })} /></td>{(["requiresVendor", "requiresCustomer", "requiresAsset", "requiresCostCenter"] as const).map((field) => <td key={field} className="p-2 text-center"><Switch checked={Boolean(row[field])} onChange={(event) => update(index, { [field]: event.target.checked })} /></td>)}<td className="p-2"><Input type="number" value={row.priority} onChange={(event) => update(index, { priority: Number(event.target.value) })} /></td><td className="p-2"><div className="flex items-center gap-2"><Switch checked={row.active} onChange={(event) => update(index, { active: event.target.checked })} /><Badge variant={row.active ? "success" : "neutral"}>{row.active ? "Active" : "Inactive"}</Badge></div></td></tr>)}</tbody></table></CardContent></Card>
    <SettingsFormActions dirty={dirty} saving={save.isPending} onCancel={() => setRows(structuredClone(query.data ?? []))} onSave={() => save.mutate(rows)} saveLabel="Save mapping changes" />
  </div>;
}
