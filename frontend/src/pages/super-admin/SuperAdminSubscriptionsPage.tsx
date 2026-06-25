import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, PackageCheck, Plus } from "lucide-react";
import type { SubscriptionPlan, SubscriptionPlanInput } from "@/types";
import { superAdminApi } from "@/services/superAdminApi";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { MetricCard } from "@/components/common/MetricCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/useToast";
import { formatCurrency, formatNumber } from "@/utils/formatters";

const initialPlan: SubscriptionPlanInput = { name: "Growth", monthlyPrice: 499, includedFiles: 10000, includedStorageGb: 500, includedUsers: 50, overageRate: 0.08, active: true };

function PlanForm({ value, onChange }: { value: SubscriptionPlanInput; onChange: (value: SubscriptionPlanInput) => void }) {
  const number = (key: keyof Pick<SubscriptionPlanInput, "monthlyPrice" | "includedFiles" | "includedStorageGb" | "includedUsers" | "overageRate">, raw: string) => onChange({ ...value, [key]: Number(raw) || 0 });
  return <div className="grid gap-4 md:grid-cols-2">
    <div className="space-y-2"><Label>Plan family</Label><Select value={value.name} onValueChange={(name) => onChange({ ...value, name: name as SubscriptionPlanInput["name"] })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="Starter">Starter</SelectItem><SelectItem value="Growth">Growth</SelectItem><SelectItem value="Enterprise">Enterprise</SelectItem></SelectContent></Select></div>
    <div className="space-y-2"><Label htmlFor="monthlyPrice">Monthly price (USD)</Label><Input id="monthlyPrice" type="number" min={0} value={value.monthlyPrice} onChange={(event) => number("monthlyPrice", event.target.value)} /></div>
    <div className="space-y-2"><Label htmlFor="includedFiles">Included files</Label><Input id="includedFiles" type="number" min={0} value={value.includedFiles} onChange={(event) => number("includedFiles", event.target.value)} /></div>
    <div className="space-y-2"><Label htmlFor="includedStorage">Storage (GB)</Label><Input id="includedStorage" type="number" min={0} value={value.includedStorageGb} onChange={(event) => number("includedStorageGb", event.target.value)} /></div>
    <div className="space-y-2"><Label htmlFor="includedUsers">Included users</Label><Input id="includedUsers" type="number" min={1} value={value.includedUsers} onChange={(event) => number("includedUsers", event.target.value)} /></div>
    <div className="space-y-2"><Label htmlFor="overageRate">Overage per file</Label><Input id="overageRate" type="number" min={0} step="0.01" value={value.overageRate} onChange={(event) => number("overageRate", event.target.value)} /></div>
    <div className="md:col-span-2"><Switch label="Plan version is available for assignment" checked={value.active} onChange={(event) => onChange({ ...value, active: event.target.checked })} /></div>
  </div>;
}

export function SuperAdminSubscriptionsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [newOpen, setNewOpen] = useState(false);
  const [newPlan, setNewPlan] = useState<SubscriptionPlanInput>(initialPlan);
  const [editing, setEditing] = useState<SubscriptionPlan | null>(null);
  const [editPlan, setEditPlan] = useState<SubscriptionPlanInput>(initialPlan);
  const plans = useQuery({ queryKey: ["super-admin", "subscriptions"], queryFn: superAdminApi.getSubscriptions });
  const refresh = async () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["super-admin", "subscriptions"] }),
    queryClient.invalidateQueries({ queryKey: ["super-admin", "dashboard"] }),
    queryClient.invalidateQueries({ queryKey: ["super-admin", "audit"] }),
  ]);
  const create = useMutation({
    mutationFn: superAdminApi.createSubscriptionPlan,
    onSuccess: async (plan) => { await refresh(); setNewOpen(false); setNewPlan(initialPlan); toast.success("Plan version created", `${plan.name} entitlements are ready for tenant assignment.`); },
    onError: (error) => toast.error("Plan creation failed", error instanceof Error ? error.message : "Unable to create plan version."),
  });
  const update = useMutation({
    mutationFn: ({ id, value }: { id: string; value: SubscriptionPlanInput }) => superAdminApi.updateSubscriptionPlan(id, value),
    onSuccess: async (plan) => { await refresh(); setEditing(null); toast.success("Plan controls updated", `${plan.name} pricing and entitlements were saved.`); },
    onError: (error) => toast.error("Plan update failed", error instanceof Error ? error.message : "Unable to update plan."),
  });
  if (plans.isLoading) return <LoadingState label="Loading subscription plans..." />;
  const data = plans.data ?? [];
  const openEditor = (plan: SubscriptionPlan) => {
    setEditing(plan);
    setEditPlan({ name: plan.name, monthlyPrice: plan.monthlyPrice, includedFiles: plan.includedFiles, includedStorageGb: plan.includedStorageGb, includedUsers: plan.includedUsers, overageRate: plan.overageRate, active: plan.active });
  };
  return (
    <>
      <PageHeader eyebrow="Commercial administration" title="Subscriptions" description="Manage plan entitlements, usage allowances, overage policies, and tenant distribution." actions={<Button onClick={() => setNewOpen(true)}><Plus className="h-4 w-4" />New plan version</Button>} />
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MetricCard label="Active plans" value={String(data.filter((plan) => plan.active).length)} icon={PackageCheck} />
        <MetricCard label="Subscribed companies" value={formatNumber(data.reduce((sum, plan) => sum + plan.companies, 0))} tone="info" icon={PackageCheck} />
        <MetricCard label="Base recurring value" value={formatCurrency(data.reduce((sum, plan) => sum + plan.monthlyPrice * plan.companies, 0), "USD")} tone="success" icon={PackageCheck} />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        {data.map((plan) => (
          <Card key={plan.id} className={plan.name === "Enterprise" ? "border-indigo-300 dark:border-indigo-800" : undefined}>
            <CardHeader><div className="flex items-center justify-between"><CardTitle>{plan.name}</CardTitle>{plan.name === "Enterprise" ? <Badge variant="brand">Strategic</Badge> : null}</div><CardDescription>{plan.companies} companies currently subscribed</CardDescription></CardHeader>
            <CardContent>
              <p className="text-3xl font-bold tabular">{formatCurrency(plan.monthlyPrice, "USD")}<span className="text-sm font-normal text-slate-500"> / month</span></p>
              <div className="mt-5 space-y-3 text-sm">{[
                `${formatNumber(plan.includedFiles)} files / month`, `${formatNumber(plan.includedStorageGb)} GB storage`, `${formatNumber(plan.includedUsers)} users`, `${formatCurrency(plan.overageRate, "USD")} per excess file`,
              ].map((feature) => <p key={feature} className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" />{feature}</p>)}</div>
              <Button variant="outline" className="mt-6 w-full" onClick={() => openEditor(plan)}>Edit plan controls</Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={newOpen} onOpenChange={setNewOpen}><DialogContent className="max-w-2xl"><DialogHeader><DialogTitle>Create plan version</DialogTitle><DialogDescription>Create a new pricing and entitlement version. Existing subscribers remain associated with their current records.</DialogDescription></DialogHeader><PlanForm value={newPlan} onChange={setNewPlan} /><div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setNewOpen(false)}>Cancel</Button><Button disabled={create.isPending} onClick={() => create.mutate(newPlan)}>{create.isPending ? "Creating..." : "Create plan version"}</Button></div></DialogContent></Dialog>
      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}><DialogContent className="max-w-2xl"><DialogHeader><DialogTitle>Edit {editing?.name} controls</DialogTitle><DialogDescription>Update pricing, capacity entitlements, overage rates, and plan availability.</DialogDescription></DialogHeader><PlanForm value={editPlan} onChange={setEditPlan} /><div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button><Button disabled={!editing || update.isPending} onClick={() => editing && update.mutate({ id: editing.id, value: editPlan })}>{update.isPending ? "Saving..." : "Save plan controls"}</Button></div></DialogContent></Dialog>
    </>
  );
}
