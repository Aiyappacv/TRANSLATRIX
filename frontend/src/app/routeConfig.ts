import { permissions, type Permission } from "@/utils/permissions";

export interface NavItem {
  label: string;
  path: string;
  icon: string;
  permissions?: Permission[];
  badge?: string;
  children?: NavItem[];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard", path: "/app/dashboard", icon: "LayoutDashboard", permissions: [permissions.dashboardRead] },
      { label: "Design System", path: "/app/design-system", icon: "Palette", permissions: [permissions.settingsManage] },
    ],
  },
  {
    label: "Platform",
    items: [
      { label: "Client Companies", path: "/app/platform/companies", icon: "Crown", permissions: [permissions.platformManage] },
    ],
  },
  {
    label: "Company Setup",
    items: [
      { label: "Onboarding", path: "/app/onboarding", icon: "Rocket", permissions: [permissions.onboardingManage] },
      { label: "Company Profile", path: "/app/settings/company", icon: "Building2", permissions: [permissions.settingsManage] },
      { label: "Users & Roles", path: "/app/settings/users-roles", icon: "UsersRound", permissions: [permissions.usersManage] },
    ],
  },
  {
    label: "Ingestion",
    items: [
      { label: "Data Ingestion", path: "/app/ingestion/data-ingestion", icon: "Database", permissions: [permissions.ingestionManage], children: [
        { label: "Document Extraction", path: "/app/ingestion/data-ingestion/document-extraction", icon: "ScanLine", permissions: [permissions.ingestionManage] },
      ] },
      { label: "Shared Links", path: "/app/ingestion/shared-links", icon: "Link2", permissions: [permissions.ingestionManage] },
      { label: "Batches", path: "/app/ingestion/batches", icon: "Layers3", permissions: [permissions.ingestionManage] },
    ],
  },
  {
    label: "Processing",
    items: [
      { label: "Financial Entries", path: "/app/entries", icon: "TableProperties", permissions: [permissions.entriesRead] },
      { label: "Review Queue", path: "/app/review", icon: "ClipboardCheck", permissions: [permissions.reviewRead] },
      { label: "Validation Issues", path: "/app/entries/issues", icon: "ShieldAlert", permissions: [permissions.entriesRead] },
    ],
  },
  {
    label: "Posting",
    items: [
      { label: "SAP Posting", path: "/app/posting/sap", icon: "Send", permissions: [permissions.postingRead] },
      { label: "Accounting Software Posting", path: "/app/integrations/accounting", icon: "ReceiptText", permissions: [permissions.integrationsRead] },
    ],
  },
  {
    label: "Integrations",
    items: [
      { label: "SAP S/4HANA", path: "/app/integrations/sap/settings", icon: "Cable", permissions: [permissions.integrationsManage] },
      { label: "Accounting Software", path: "/app/integrations/accounting", icon: "PlugZap", permissions: [permissions.integrationsRead] },
      { label: "Tally Export", path: "/app/integrations/tally-export", icon: "ReceiptText", permissions: [permissions.integrationsRead] },
      { label: "ERP", path: "/app/integrations/accounting?type=erp", icon: "Cable", permissions: [permissions.integrationsRead] },
      { label: "Workday", path: "/app/integrations/workday", icon: "UsersRound", permissions: [permissions.integrationsRead] },
      { label: "ServiceNow", path: "/app/integrations/servicenow", icon: "Webhook", permissions: [permissions.integrationsRead] },
      { label: "API Connectors", path: "/app/integrations/webhook_api", icon: "Webhook", permissions: [permissions.integrationsRead] },
    ],
  },
  {
    label: "Monitoring",
    items: [
      { label: "Analytics", path: "/app/analytics", icon: "BarChart3", permissions: [permissions.analyticsRead] },
      { label: "Approval History", path: "/app/review/history", icon: "History", permissions: [permissions.reviewRead, permissions.auditRead] },
      { label: "Audit Logs", path: "/app/audit", icon: "ListChecks", permissions: [permissions.auditRead] },
      { label: "Processing Logs", path: "/app/monitoring/processing-logs", icon: "ScrollText", permissions: [permissions.auditRead] },
      { label: "Error Center", path: "/app/monitoring/error-center", icon: "ShieldAlert", permissions: [permissions.auditRead, permissions.integrationsManage, permissions.postingRetry] },
    ],
  },
  {
    label: "Administration",
    items: [
      { label: "Company Settings", path: "/app/settings/company", icon: "Settings", permissions: [permissions.settingsManage] },
      { label: "Users & Roles", path: "/app/settings/users-roles", icon: "UsersRound", permissions: [permissions.usersManage] },
      { label: "Approval Rules", path: "/app/settings/approval-rules", icon: "CheckSquare", permissions: [permissions.settingsManage] },
      { label: "SAP T-Code Mapping", path: "/app/settings/sap-tcode-mapping", icon: "GitBranch", permissions: [permissions.settingsManage] },
      { label: "GL Mapping", path: "/app/settings/gl-account-mapping", icon: "TableProperties", permissions: [permissions.settingsManage] },
      { label: "Document Processing", path: "/app/settings/ocr", icon: "ScanLine", permissions: [permissions.settingsManage] },
      { label: "Security Settings", path: "/app/settings/security", icon: "ShieldCheck", permissions: [permissions.settingsManage] },
    ],
  },
];
