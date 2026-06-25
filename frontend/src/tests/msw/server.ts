import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const server = setupServer(
  http.get("/api/v1/health", () => HttpResponse.json({ status: "ok", service: "translatrix-frontend-test" })),
  http.post("/api/v1/frontend/entries/:id/validate", async ({ request }) => {
    const candidate = await request.json() as { accountingEntry: { debitLines: Array<{ amount: number }>; creditLines: Array<{ amount: number }> } };
    const debit = candidate.accountingEntry.debitLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
    const credit = candidate.accountingEntry.creditLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
    const balanced = Math.abs(debit - credit) < 0.01;
    return HttpResponse.json({
      validationStatus: balanced ? "valid" : "failed",
      issues: balanced ? [] : [{ code: "ACCOUNTING_UNBALANCED", severity: "error", message: "Debit and credit totals must match.", field: "accountingEntry" }],
    });
  }),
);
