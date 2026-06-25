import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export function ConfirmDialog({ trigger, title, description, confirmLabel = "Confirm", destructive = true, onConfirm }: { trigger: ReactNode; title: string; description: string; confirmLabel?: string; destructive?: boolean; onConfirm?: () => void | Promise<void> }) {
  const [pending, setPending] = useState(false);
  const confirm = async () => { setPending(true); try { await onConfirm?.(); } finally { setPending(false); } };
  return <Dialog><DialogTrigger asChild>{trigger}</DialogTrigger><DialogContent><DialogHeader><DialogTitle>{title}</DialogTitle><DialogDescription>{description}</DialogDescription></DialogHeader><div className="flex justify-end gap-2"><DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose><DialogClose asChild><Button variant={destructive ? "destructive" : "default"} disabled={pending} onClick={confirm}>{pending ? "Working..." : confirmLabel}</Button></DialogClose></div></DialogContent></Dialog>;
}
