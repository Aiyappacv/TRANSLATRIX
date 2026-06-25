export interface Company {
  id: string;
  tenantId: string;
  legalName: string;
  tradingName?: string;
  country: string;
  industry?: string;
  registrationNumber?: string;
  taxId: string;
  defaultCurrency: string;
  defaultCompanyCode: string;
  fiscalYearVariant: string;
  financeContact: string;
  status: "pending" | "active" | "suspended";
  registeredBy?: string;
  companyAdminEmail?: string;
  plan?: "Starter" | "Growth" | "Enterprise";
  tokenLimit?: number;
  tokenUsage?: number;
}
