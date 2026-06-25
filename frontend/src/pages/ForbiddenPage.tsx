import { Lock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
export function ForbiddenPage() {
  return <Card><CardContent className="p-10 text-center"><Lock className="mx-auto mb-4 h-10 w-10 text-danger" /><h1 className="text-2xl font-bold">Forbidden</h1><p className="mt-2 text-slate-500">You do not have permission to access this page.</p></CardContent></Card>;
}
