import { AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export function AlertCard({ title, description }: { title: string; description: string }) {
  return <Card className="border-warning/40 bg-warning/10"><CardContent className="flex gap-3 p-4 text-warning"><AlertTriangle className="h-5 w-5" /><div><p className="font-semibold">{title}</p><p className="text-sm">{description}</p></div></CardContent></Card>;
}
