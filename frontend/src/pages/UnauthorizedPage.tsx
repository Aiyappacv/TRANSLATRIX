import { ShieldAlert } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
export function UnauthorizedPage() {
  return <Card><CardContent className="p-10 text-center"><ShieldAlert className="mx-auto mb-4 h-10 w-10 text-warning" /><h1 className="text-2xl font-bold">Unauthorized</h1><p className="mt-2 text-slate-500">Please sign in to continue.</p></CardContent></Card>;
}
