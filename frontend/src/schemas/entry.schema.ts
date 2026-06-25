import { z } from "zod";

export const entryUpdateSchema = z.object({
  category: z.enum(["Expenses", "Income", "Assets", "Liabilities"]),
  subcategory: z.string().min(2),
  date: z.string().min(4),
  amount: z.number(),
  currency: z.string().min(3).max(3),
  vendor: z.string().optional(),
  customer: z.string().optional(),
  reference: z.string().min(1),
  invoiceNumber: z.string().optional(),
  glAccount: z.string().min(3),
  sapTCode: z.string().min(2),
  operation: z.string().min(2),
  costCenter: z.string().optional(),
  taxCode: z.string().optional(),
});
