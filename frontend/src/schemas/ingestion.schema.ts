import { z } from "zod";

export const sharedLinkSourceTypes = [
  "Google Drive",
  "OneDrive",
  "SharePoint",
  "Dropbox",
  "SFTP",
  "AWS S3",
  "Azure Blob",
  "Manual URL",
  "Local Upload",
] as const;

export const sharedLinkAuthTypes = ["None", "OAuth", "Service Account", "API Key", "Basic Auth", "SFTP Key", "SAS Token"] as const;
export const sharedLinkScheduleModes = ["Manual", "Hourly", "Every 2 hours", "Daily", "Weekly"] as const;

export const sharedLinkSchema = z.object({
  clientName: z.string().min(2, "Client name is required"),
  sourceType: z.enum(sharedLinkSourceTypes),
  provider: z.enum(sharedLinkSourceTypes).optional(),
  name: z.string().min(2, "Source name is required"),
  url: z.string(),
  authenticationType: z.enum(sharedLinkAuthTypes),
  folderPath: z.string().min(1, "Folder path is required"),
  fileFilters: z.string().min(1, "File filters are required"),
  schedule: z.enum(sharedLinkScheduleModes),
  defaultCompanyCode: z.string().min(2, "Default company code is required"),
  defaultCurrency: z.string().min(3, "Default currency is required").max(3),
  defaultReviewerGroup: z.string().min(2, "Reviewer group is required"),
  defaultAccountingIntegration: z.string().min(2, "Accounting integration is required"),
  allowedDomain: z.string().min(2).optional(),
}).superRefine((value, context) => {
  if (value.sourceType !== "Local Upload" && value.url.trim().length < 6) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: ["url"], message: "Shared URL or endpoint is required" });
  }
});

export type SharedLinkInput = z.infer<typeof sharedLinkSchema>;
