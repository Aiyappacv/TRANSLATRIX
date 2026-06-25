import { Eye, ShieldCheck } from "lucide-react";
import { Alert } from "@/components/ui/alert";

export function TenantAuditBanner() {
  return (
    <Alert tone="warning" className="mb-5 flex items-start gap-3">
      <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0" />
      <div>
        <p className="font-semibold">You are viewing tenant data as a Super Admin</p>
        <p className="mt-1 text-xs leading-5 opacity-90">
          Every view, export, configuration change, support action, and tenant-context switch is written to the immutable platform audit log.
        </p>
      </div>
      <Eye className="ml-auto hidden h-5 w-5 shrink-0 sm:block" />
    </Alert>
  );
}
