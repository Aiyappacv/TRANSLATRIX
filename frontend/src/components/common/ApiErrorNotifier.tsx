import { useEffect } from "react";
import { toast } from "sonner";
import type { ApiClientError } from "@/services/apiClient";

export function ApiErrorNotifier() {
  useEffect(() => {
    const notify = (event: Event) => {
      const error = (event as CustomEvent<ApiClientError>).detail;
      if (!error) return;
      const description = error.status
        ? `Request failed with status ${error.status}${error.code ? ` (${error.code})` : ""}.`
        : "The backend request could not be completed.";
      toast.error(error.message || "API request failed", { description });
    };
    window.addEventListener("translatrix:api-error", notify);
    return () => window.removeEventListener("translatrix:api-error", notify);
  }, []);

  return null;
}
