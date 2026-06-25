import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function RetryActionButton({ retryable, pending, onRetry }: { retryable: boolean; pending?: boolean; onRetry: () => void }) {
  return <Button size="sm" variant="outline" disabled={!retryable || pending} onClick={onRetry} aria-label={retryable ? "Retry failed operation" : "Operation is not retryable"}><RefreshCw className={`h-4 w-4 ${pending ? "animate-spin" : ""}`} />{pending ? "Retrying" : retryable ? "Retry" : "Manual fix"}</Button>;
}
