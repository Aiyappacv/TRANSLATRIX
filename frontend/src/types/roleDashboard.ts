import type { RoleCode } from "./auth";

export type DashboardTone = "success" | "warning" | "danger" | "info" | "neutral";

export interface RoleDashboardKpi {
  key: string;
  label: string;
  value: string;
  delta: string;
  tone: DashboardTone;
  icon: string;
}

export interface DashboardTask {
  id: string;
  title: string;
  description: string;
  status: "pending" | "attention" | "completed";
  href: string;
  dueLabel?: string;
}

export interface DashboardRecentEntry {
  id: string;
  description: string;
  category: string;
  amount: string;
  status: string;
}

export interface DashboardStatusItem {
  label: string;
  value: string;
  tone: DashboardTone;
  detail: string;
}

export interface RoleDashboardDefinition {
  role: RoleCode;
  title: string;
  subtitle: string;
  focus: string;
  readOnly?: boolean;
  kpis: RoleDashboardKpi[];
  tasks: DashboardTask[];
  processing: DashboardStatusItem[];
  sapPosting: DashboardStatusItem[];
  validation: DashboardStatusItem[];
  integrations: DashboardStatusItem[];
  categoryBreakdown: Array<{ category: string; value: number }>;
  recentFiles: Array<{ id: string; name: string; status: string; createdAt: string }>;
  recentEntries: DashboardRecentEntry[];
  auditActivity: Array<{ id: string; actor: string; action: string; timestamp: string }>;
  quickActions: Array<{ label: string; href: string; permission?: string }>;
}
