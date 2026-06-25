import { permissions, type Permission } from "@/utils/permissions";

export interface SuperAdminNavItem {
  label: string;
  path: string;
  icon: string;
  permission: Permission;
  badge?: string;
}

export interface SuperAdminNavGroup {
  label: string;
  items: SuperAdminNavItem[];
}

export const superAdminNavGroups: SuperAdminNavGroup[] = [
  {
    label: "Platform",
    items: [
      { label: "Dashboard", path: "/super-admin/dashboard", icon: "LayoutDashboard", permission: permissions.platformDashboardRead },
      { label: "Companies", path: "/super-admin/companies", icon: "Building2", permission: permissions.platformCompaniesManage },
      { label: "Company onboarding", path: "/super-admin/company-onboarding", icon: "Building2", permission: permissions.platformCompaniesManage },
    ],
  },
  {
    label: "Commercial",
    items: [
      { label: "Subscriptions", path: "/super-admin/subscriptions", icon: "BadgeDollarSign", permission: permissions.platformBillingManage },
      { label: "Billing", path: "/super-admin/billing", icon: "CreditCard", permission: permissions.platformBillingManage },
      { label: "Usage analytics", path: "/super-admin/usage-analytics", icon: "ChartNoAxesCombined", permission: permissions.platformUsageRead },
    ],
  },
  {
    label: "Operations",
    items: [
      { label: "Integrations", path: "/super-admin/integrations", icon: "Network", permission: permissions.platformIntegrationsMonitor },
      { label: "System health", path: "/super-admin/system-health", icon: "Activity", permission: permissions.platformHealthRead },
      { label: "Job queues", path: "/super-admin/job-queues", icon: "ListTodo", permission: permissions.platformQueuesManage },
      { label: "Error center", path: "/super-admin/error-center", icon: "ShieldAlert", permission: permissions.platformErrorsManage },
    ],
  },
  {
    label: "Governance",
    items: [
      { label: "Audit logs", path: "/super-admin/audit-logs", icon: "ScrollText", permission: permissions.platformAuditRead },
      { label: "Support", path: "/super-admin/support", icon: "LifeBuoy", permission: permissions.platformSupportManage },
      { label: "Settings", path: "/super-admin/settings", icon: "Settings", permission: permissions.platformSettingsManage },
    ],
  },
];
