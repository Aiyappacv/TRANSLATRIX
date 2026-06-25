import { lazy, Suspense, type ReactElement } from "react";
import { Navigate, Outlet, createBrowserRouter } from "react-router-dom";
import { ProtectedRoute } from "./protectedRoute";
import { AccessRoute } from "./AccessRoute";
import { permissions, type Permission } from "@/utils/permissions";
import { AuthLayout } from "@/layouts/AuthLayout";
import { DashboardLayout } from "@/layouts/DashboardLayout";
import { SuperAdminLayout } from "@/layouts/SuperAdminLayout";
import { LoadingState } from "@/components/common/LoadingState";

const LoginPage = lazy(() => import("@/pages/auth/LoginPage").then((module) => ({ default: module.LoginPage })));
const RegisterCompanyPage = lazy(() => import("@/pages/auth/RegisterCompanyPage").then((module) => ({ default: module.RegisterCompanyPage })));
const ForgotPasswordPage = lazy(() => import("@/pages/auth/ForgotPasswordPage").then((module) => ({ default: module.ForgotPasswordPage })));
const ResetPasswordPage = lazy(() => import("@/pages/auth/ResetPasswordPage").then((module) => ({ default: module.ResetPasswordPage })));
const RoleBasedDashboardRouter = lazy(() => import("@/pages/dashboard/RoleBasedDashboardRouter").then((module) => ({ default: module.RoleBasedDashboardRouter })));
const ClientCompaniesPage = lazy(() => import("@/pages/platform/ClientCompaniesPage").then((module) => ({ default: module.ClientCompaniesPage })));
const OnboardingPage = lazy(() => import("@/pages/onboarding/OnboardingPage").then((module) => ({ default: module.OnboardingPage })));
const CompanyOnboardingWizardPage = lazy(() => import("@/pages/onboarding/CompanyOnboardingWizardPage").then((module) => ({ default: module.CompanyOnboardingWizardPage })));
const OnboardingCompletePage = lazy(() => import("@/pages/onboarding/OnboardingCompletePage").then((module) => ({ default: module.OnboardingCompletePage })));
const SharedLinksPage = lazy(() => import("@/pages/ingestion/SharedLinksPage").then((module) => ({ default: module.SharedLinksPage })));
const CreateSharedLinkPage = lazy(() => import("@/pages/ingestion/CreateSharedLinkPage").then((module) => ({ default: module.CreateSharedLinkPage })));
const SharedLinkDetailPage = lazy(() => import("@/pages/ingestion/SharedLinkDetailPage").then((module) => ({ default: module.SharedLinkDetailPage })));
const BatchesPage = lazy(() => import("@/pages/batches/BatchesPage").then((module) => ({ default: module.BatchesPage })));
const BatchDetailPage = lazy(() => import("@/pages/batches/BatchDetailPage").then((module) => ({ default: module.BatchDetailPage })));
const DataIngestionPage = lazy(() => import("@/pages/ingestion/DataIngestionPage").then((module) => ({ default: module.DataIngestionPage })));
const DocumentExtractionPage = lazy(() => import("@/pages/ingestion/DocumentExtractionPage").then((module) => ({ default: module.DocumentExtractionPage })));
const FilesPage = lazy(() => import("@/pages/files/FilesPage").then((module) => ({ default: module.FilesPage })));
const FileDetailPage = lazy(() => import("@/pages/files/FileDetailPage").then((module) => ({ default: module.FileDetailPage })));
const DocumentRegistryPage = lazy(() => import("@/pages/files/DocumentRegistryPage").then((module) => ({ default: module.DocumentRegistryPage })));
const DocumentRegistryDetailPage = lazy(() => import("@/pages/files/DocumentRegistryDetailPage").then((module) => ({ default: module.DocumentRegistryDetailPage })));
const FinancialEntriesPage = lazy(() => import("@/pages/entries/FinancialEntriesPage").then((module) => ({ default: module.FinancialEntriesPage })));
const FinancialEntryDetailPage = lazy(() => import("@/pages/entries/FinancialEntryDetailPage").then((module) => ({ default: module.FinancialEntryDetailPage })));
const ValidationIssuesPage = lazy(() => import("@/pages/entries/ValidationIssuesPage").then((module) => ({ default: module.ValidationIssuesPage })));
const ReviewQueuePage = lazy(() => import("@/pages/review/ReviewQueuePage").then((module) => ({ default: module.ReviewQueuePage })));
const ReviewTaskDetailPage = lazy(() => import("@/pages/review/ReviewTaskDetailPage").then((module) => ({ default: module.ReviewTaskDetailPage })));
const ApprovalHistoryPage = lazy(() => import("@/pages/review/ApprovalHistoryPage").then((module) => ({ default: module.ApprovalHistoryPage })));
const SapPostingPage = lazy(() => import("@/pages/sap/SapPostingPage").then((module) => ({ default: module.SapPostingPage })));
const SapPostingDetailPage = lazy(() => import("@/pages/sap/SapPostingDetailPage").then((module) => ({ default: module.SapPostingDetailPage })));
const SapIntegrationSettingsPage = lazy(() => import("@/pages/sap/SapIntegrationSettingsPage").then((module) => ({ default: module.SapIntegrationSettingsPage })));
const AccountingIntegrationsPage = lazy(() => import("@/pages/integrations/AccountingIntegrationsPage").then((module) => ({ default: module.AccountingIntegrationsPage })));
const IntegrationDetailPage = lazy(() => import("@/pages/integrations/IntegrationDetailPage").then((module) => ({ default: module.IntegrationDetailPage })));
const TallyExportPage = lazy(() => import("@/pages/integrations/TallyExportPage").then((module) => ({ default: module.TallyExportPage })));
const AnalyticsPage = lazy(() => import("@/pages/analytics/AnalyticsPage").then((module) => ({ default: module.AnalyticsPage })));
const AuditLogsPage = lazy(() => import("@/pages/audit/AuditLogsPage").then((module) => ({ default: module.AuditLogsPage })));
const ProcessingLogsPage = lazy(() => import("@/pages/monitoring/ProcessingLogsPage").then((module) => ({ default: module.ProcessingLogsPage })));
const MappingSettingsPage = lazy(() => import("@/pages/settings/MappingSettingsPage").then((module) => ({ default: module.MappingSettingsPage })));
const SapTCodeMappingPage = lazy(() => import("@/pages/settings/SapTCodeMappingPage").then((module) => ({ default: module.SapTCodeMappingPage })));
const GLAccountMappingPage = lazy(() => import("@/pages/settings/GLAccountMappingPage").then((module) => ({ default: module.GLAccountMappingPage })));
const CompanySettingsPage = lazy(() => import("@/pages/settings/CompanySettingsPage").then((module) => ({ default: module.CompanySettingsPage })));
const UsersAndRolesPage = lazy(() => import("@/pages/settings/UsersAndRolesPage").then((module) => ({ default: module.UsersAndRolesPage })));
const ApprovalRulesPage = lazy(() => import("@/pages/settings/ApprovalRulesPage").then((module) => ({ default: module.ApprovalRulesPage })));
const OCRSettingsPage = lazy(() => import("@/pages/settings/OCRSettingsPage").then((module) => ({ default: module.OCRSettingsPage })));
const SecuritySettingsPage = lazy(() => import("@/pages/settings/SecuritySettingsPage").then((module) => ({ default: module.SecuritySettingsPage })));
const ErrorCenterPage = lazy(() => import("@/pages/monitoring/ErrorCenterPage").then((module) => ({ default: module.ErrorCenterPage })));
const DesignSystemPage = lazy(() => import("@/pages/design-system/DesignSystemPage").then((module) => ({ default: module.DesignSystemPage })));
const SuperAdminDashboardPage = lazy(() => import("@/pages/super-admin/SuperAdminDashboardPage").then((module) => ({ default: module.SuperAdminDashboardPage })));
const SuperAdminCompaniesPage = lazy(() => import("@/pages/super-admin/SuperAdminCompaniesPage").then((module) => ({ default: module.SuperAdminCompaniesPage })));
const SuperAdminCompanyDetailPage = lazy(() => import("@/pages/super-admin/SuperAdminCompanyDetailPage").then((module) => ({ default: module.SuperAdminCompanyDetailPage })));
const SuperAdminCompanyOnboardingPage = lazy(() => import("@/pages/super-admin/SuperAdminCompanyOnboardingPage").then((module) => ({ default: module.SuperAdminCompanyOnboardingPage })));
const SuperAdminSubscriptionsPage = lazy(() => import("@/pages/super-admin/SuperAdminSubscriptionsPage").then((module) => ({ default: module.SuperAdminSubscriptionsPage })));
const SuperAdminBillingPage = lazy(() => import("@/pages/super-admin/SuperAdminBillingPage").then((module) => ({ default: module.SuperAdminBillingPage })));
const SuperAdminIntegrationsPage = lazy(() => import("@/pages/super-admin/SuperAdminIntegrationsPage").then((module) => ({ default: module.SuperAdminIntegrationsPage })));
const SuperAdminSystemHealthPage = lazy(() => import("@/pages/super-admin/SuperAdminSystemHealthPage").then((module) => ({ default: module.SuperAdminSystemHealthPage })));
const SuperAdminJobQueuesPage = lazy(() => import("@/pages/super-admin/SuperAdminJobQueuesPage").then((module) => ({ default: module.SuperAdminJobQueuesPage })));
const SuperAdminErrorCenterPage = lazy(() => import("@/pages/super-admin/SuperAdminErrorCenterPage").then((module) => ({ default: module.SuperAdminErrorCenterPage })));
const SuperAdminUsageAnalyticsPage = lazy(() => import("@/pages/super-admin/SuperAdminUsageAnalyticsPage").then((module) => ({ default: module.SuperAdminUsageAnalyticsPage })));
const SuperAdminAuditLogsPage = lazy(() => import("@/pages/super-admin/SuperAdminAuditLogsPage").then((module) => ({ default: module.SuperAdminAuditLogsPage })));
const SuperAdminSupportPage = lazy(() => import("@/pages/super-admin/SuperAdminSupportPage").then((module) => ({ default: module.SuperAdminSupportPage })));
const SuperAdminSettingsPage = lazy(() => import("@/pages/super-admin/SuperAdminSettingsPage").then((module) => ({ default: module.SuperAdminSettingsPage })));
const ForbiddenPage = lazy(() => import("@/pages/ForbiddenPage").then((module) => ({ default: module.ForbiddenPage })));
const UnauthorizedPage = lazy(() => import("@/pages/UnauthorizedPage").then((module) => ({ default: module.UnauthorizedPage })));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })));
const MaintenancePage = lazy(() => import("@/pages/MaintenancePage").then((module) => ({ default: module.MaintenancePage })));

const suspense = (element: ReactElement) => <Suspense fallback={<LoadingState />}>{element}</Suspense>;
const secure = (element: ReactElement, requiredPermissions?: Permission[]) => (
  <AccessRoute permissions={requiredPermissions}>{suspense(element)}</AccessRoute>
);

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/app/dashboard" replace /> },
  { path: "/maintenance", element: suspense(<MaintenancePage />) },
  {
    path: "/auth",
    element: <AuthLayout />,
    children: [
      { path: "login", element: suspense(<LoginPage />) },
      { path: "forgot-password", element: suspense(<ForgotPasswordPage />) },
      { path: "reset-password", element: suspense(<ResetPasswordPage />) },
      { path: "register", element: suspense(<RegisterCompanyPage />) },
    ],
  },
  {
    path: "/super-admin",
    element: <ProtectedRoute requiredPermissions={[permissions.platformDashboardRead]} />,
    children: [
      {
        element: <SuperAdminLayout />,
        children: [
          { index: true, element: <Navigate to="dashboard" replace /> },
          { path: "dashboard", element: secure(<SuperAdminDashboardPage />, [permissions.platformDashboardRead]) },
          { path: "companies", element: secure(<SuperAdminCompaniesPage />, [permissions.platformCompaniesManage]) },
          { path: "companies/:companyId", element: secure(<SuperAdminCompanyDetailPage />, [permissions.platformTenantView]) },
          { path: "company-onboarding", element: secure(<SuperAdminCompanyOnboardingPage />, [permissions.platformCompaniesManage]) },
          { path: "subscriptions", element: secure(<SuperAdminSubscriptionsPage />, [permissions.platformBillingManage]) },
          { path: "billing", element: secure(<SuperAdminBillingPage />, [permissions.platformBillingManage]) },
          { path: "integrations", element: secure(<SuperAdminIntegrationsPage />, [permissions.platformIntegrationsMonitor]) },
          { path: "system-health", element: secure(<SuperAdminSystemHealthPage />, [permissions.platformHealthRead]) },
          { path: "job-queues", element: secure(<SuperAdminJobQueuesPage />, [permissions.platformQueuesManage]) },
          { path: "error-center", element: secure(<SuperAdminErrorCenterPage />, [permissions.platformErrorsManage]) },
          { path: "usage-analytics", element: secure(<SuperAdminUsageAnalyticsPage />, [permissions.platformUsageRead]) },
          { path: "audit-logs", element: secure(<SuperAdminAuditLogsPage />, [permissions.platformAuditRead]) },
          { path: "support", element: secure(<SuperAdminSupportPage />, [permissions.platformSupportManage]) },
          { path: "settings", element: secure(<SuperAdminSettingsPage />, [permissions.platformSettingsManage]) },
        ],
      },
    ],
  },
  {
    path: "/app",
    element: <ProtectedRoute />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          { path: "dashboard", element: secure(<RoleBasedDashboardRouter />, [permissions.dashboardRead]) },
          { path: "dashboard/:dashboardRole", element: secure(<RoleBasedDashboardRouter />, [permissions.dashboardRead]) },
          { path: "design-system", element: secure(<DesignSystemPage />, [permissions.settingsManage]) },
          { path: "platform/companies", element: secure(<ClientCompaniesPage />, [permissions.platformManage]) },
          { path: "onboarding", element: secure(<OnboardingPage />, [permissions.onboardingManage]) },
          { path: "onboarding/wizard", element: secure(<CompanyOnboardingWizardPage />, [permissions.onboardingManage]) },
          { path: "onboarding/complete", element: secure(<OnboardingCompletePage />, [permissions.onboardingManage]) },
          {
            path: "ingestion/data-ingestion",
            element: <Outlet />,
            children: [
              { index: true, element: secure(<DataIngestionPage />, [permissions.ingestionManage]) },
              { path: "document-extraction", element: secure(<DocumentExtractionPage />, [permissions.ingestionManage]) },
            ],
          },
          { path: "ingestion/shared-links", element: secure(<SharedLinksPage />, [permissions.ingestionManage]) },
          { path: "ingestion/shared-links/new", element: secure(<CreateSharedLinkPage />, [permissions.ingestionManage]) },
          { path: "ingestion/shared-links/:linkId", element: secure(<SharedLinkDetailPage />, [permissions.ingestionManage]) },
          { path: "ingestion/batches", element: secure(<BatchesPage />, [permissions.ingestionManage]) },
          { path: "ingestion/batches/:batchId", element: secure(<BatchDetailPage />, [permissions.ingestionManage]) },
          { path: "files", element: secure(<FilesPage />, [permissions.filesRead]) },
          { path: "files/registry", element: secure(<DocumentRegistryPage />, [permissions.filesRead]) },
          { path: "files/registry/:fileId", element: secure(<DocumentRegistryDetailPage />, [permissions.filesRead]) },
          { path: "files/:fileId", element: secure(<FileDetailPage />, [permissions.filesRead]) },
          { path: "entries", element: secure(<FinancialEntriesPage />, [permissions.entriesRead]) },
          { path: "entries/issues", element: secure(<ValidationIssuesPage />, [permissions.entriesRead]) },
          { path: "entries/validation-issues", element: secure(<ValidationIssuesPage />, [permissions.entriesRead]) },
          { path: "entries/:entryId", element: secure(<FinancialEntryDetailPage />, [permissions.entriesRead]) },
          { path: "review", element: secure(<ReviewQueuePage />, [permissions.reviewRead]) },
          { path: "review/history", element: secure(<ApprovalHistoryPage />, [permissions.reviewRead, permissions.auditRead]) },
          { path: "review/:taskId", element: secure(<ReviewTaskDetailPage />, [permissions.reviewRead]) },
          { path: "posting/sap", element: secure(<SapPostingPage />, [permissions.postingRead]) },
          { path: "posting/sap/:postingId", element: secure(<SapPostingDetailPage />, [permissions.postingRead]) },
          { path: "integrations", element: secure(<AccountingIntegrationsPage />, [permissions.integrationsRead]) },
          { path: "integrations/accounting", element: secure(<AccountingIntegrationsPage />, [permissions.integrationsRead]) },
          { path: "integrations/sap/settings", element: secure(<SapIntegrationSettingsPage />, [permissions.integrationsManage]) },
          { path: "integrations/tally-export", element: secure(<TallyExportPage />, [permissions.integrationsRead]) },
          { path: "integrations/:providerCode", element: secure(<IntegrationDetailPage />, [permissions.integrationsRead]) },
          { path: "analytics", element: secure(<AnalyticsPage />, [permissions.analyticsRead]) },
          { path: "audit", element: secure(<AuditLogsPage />, [permissions.auditRead]) },
          { path: "monitoring/processing-logs", element: secure(<ProcessingLogsPage />, [permissions.auditRead]) },
          { path: "monitoring/error-center", element: secure(<ErrorCenterPage />, [permissions.auditRead, permissions.integrationsManage, permissions.postingRetry]) },
          { path: "settings/mapping", element: secure(<MappingSettingsPage />, [permissions.settingsManage]) },
          { path: "settings/sap-tcode-mapping", element: secure(<SapTCodeMappingPage />, [permissions.settingsManage]) },
          { path: "settings/gl-account-mapping", element: secure(<GLAccountMappingPage />, [permissions.settingsManage]) },
          { path: "settings/company", element: secure(<CompanySettingsPage />, [permissions.settingsManage]) },
          { path: "settings/users-roles", element: secure(<UsersAndRolesPage />, [permissions.usersManage]) },
          { path: "settings/approval-rules", element: secure(<ApprovalRulesPage />, [permissions.settingsManage]) },
          { path: "settings/ocr", element: secure(<OCRSettingsPage />, [permissions.settingsManage]) },
          { path: "settings/security", element: secure(<SecuritySettingsPage />, [permissions.settingsManage]) },
          { path: "forbidden", element: suspense(<ForbiddenPage />) },
          { path: "unauthorized", element: suspense(<UnauthorizedPage />) },
        ],
      },
    ],
  },
  { path: "*", element: suspense(<NotFoundPage />) },
]);
