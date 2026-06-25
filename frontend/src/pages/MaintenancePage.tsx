import { Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";

export function MaintenancePage() {
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6 dark:bg-navy-950"><section className="max-w-xl rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-enterprise dark:border-slate-800 dark:bg-slate-950"><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300"><Wrench className="h-7 w-7" /></div><h1 className="mt-5 text-2xl font-bold">Scheduled maintenance</h1><p className="mt-3 text-sm leading-6 text-slate-500">TRANSLATRIX PRO is temporarily unavailable while production services are being updated. No accounting data or queued jobs will be lost.</p><Button className="mt-6" onClick={() => location.reload()}>Check again</Button></section></main>;
}
