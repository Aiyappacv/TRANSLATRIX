import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface TenantCompanyOption {
  id: string;
  name: string;
  tenantId: string;
}

interface TenantState {
  activeTenantId: string | null;
  activeCompanyId: string | null;
  activeCompanyName: string | null;
  availableCompanies: TenantCompanyOption[];
  setActiveCompany: (company: TenantCompanyOption) => void;
  setAvailableCompanies: (companies: TenantCompanyOption[]) => void;
  activateUserCompany: (company: TenantCompanyOption) => void;
  clearTenant: () => void;
}

export const useTenantStore = create<TenantState>()(
  persist(
    (set) => ({
      activeTenantId: null,
      activeCompanyId: null,
      activeCompanyName: null,
      availableCompanies: [],
      setActiveCompany: (company) => set({ activeCompanyId: company.id, activeTenantId: company.tenantId, activeCompanyName: company.name }),
      setAvailableCompanies: (availableCompanies) => set({ availableCompanies }),
      activateUserCompany: (company) => set((state) => ({
        activeCompanyId: company.id,
        activeTenantId: company.tenantId,
        activeCompanyName: company.name,
        availableCompanies: state.availableCompanies.some((item) => item.id === company.id)
          ? state.availableCompanies
          : [...state.availableCompanies, company],
      })),
      clearTenant: () => set({ activeTenantId: null, activeCompanyId: null, activeCompanyName: null, availableCompanies: [] }),
    }),
    { name: "translatrix-tenant-production" },
  ),
);
