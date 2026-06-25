import { CheckCircle2, MessageSquareWarning, Send, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ApprovalActionBar({ onApprove, onReject, onRequestChanges, onPost }: { onApprove?: () => void; onReject?: () => void; onRequestChanges?: () => void; onPost?: () => void }) {
  return (
    <div className="sticky bottom-0 z-10 mt-4 rounded-2xl border border-slate-200 bg-white/90 p-3 shadow-enterprise backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
      <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
        <Button variant="success" onClick={onApprove}><CheckCircle2 className="h-4 w-4" />Approve</Button>
        <Button variant="outline" onClick={onRequestChanges}><MessageSquareWarning className="h-4 w-4" />Changes</Button>
        <Button variant="destructive" onClick={onReject}><XCircle className="h-4 w-4" />Reject</Button>
        <Button variant="default" onClick={onPost}><Send className="h-4 w-4" />Post</Button>
      </div>
    </div>
  );
}
