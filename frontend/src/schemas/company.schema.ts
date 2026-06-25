import { z } from "zod";

export const registerCompanySchema = z.object({
  legalName: z.string().min(2, "Company legal name is required"),
  tradingName: z.string().min(2, "Trading name is required"),
  country: z.string().min(2, "Country is required"),
  industry: z.string().min(2, "Industry is required"),
  registrationNumber: z.string().min(2, "Registration number is required"),
  taxId: z.string().min(3, "Tax/VAT/GST number is required"),
  primaryContactName: z.string().min(2, "Primary contact name is required"),
  primaryContactEmail: z.string().email("Use a valid email"),
  phoneNumber: z.string().min(6, "Phone number is required"),
  website: z.string().min(3, "Website is required"),
  defaultCurrency: z.string().min(3).max(3),
  defaultLanguage: z.string().min(2),
  timezone: z.string().min(2),
  preferredAccountingSystem: z.string().min(2),
});
export type RegisterCompanyInput = z.infer<typeof registerCompanySchema>;
