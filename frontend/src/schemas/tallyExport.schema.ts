import { z } from "zod";

export const tallyVoucherTypes = ["purchase", "sales", "journal", "payment", "receipt", "contra"] as const;

export const tallyExportSchema = z.object({
  companyId: z.string().min(1, "Select a company."),
  companyCode: z.string().min(2, "Company code is required.").max(12),
  dateFrom: z.string().min(1, "Start date is required."),
  dateTo: z.string().min(1, "End date is required."),
  format: z.enum(["xml", "json", "csv"]),
  voucherTypes: z.array(z.enum(tallyVoucherTypes)).min(1, "Select at least one voucher type."),
  includeLedgers: z.boolean(),
  includeCostCenters: z.boolean(),
  includeTaxDetails: z.boolean(),
}).refine((value) => value.dateTo >= value.dateFrom, {
  path: ["dateTo"],
  message: "End date must be on or after the start date.",
});

export type TallyExportForm = z.infer<typeof tallyExportSchema>;
