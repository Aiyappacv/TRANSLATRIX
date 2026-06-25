import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export function ErrorDetailDrawer({ title = "Error details", details }: { title?: string; details: string }) {
  return (
    <Dialog>
      <DialogTrigger asChild><Button variant="outline" size="sm"><AlertTriangle className="h-4 w-4" />Details</Button></DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader><DialogTitle>{title}</DialogTitle><DialogDescription>Diagnostic details and retry guidance.</DialogDescription></DialogHeader>
        <pre className="max-h-[420px] overflow-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-100">{details}</pre>
      </DialogContent>
    </Dialog>
  );
}
