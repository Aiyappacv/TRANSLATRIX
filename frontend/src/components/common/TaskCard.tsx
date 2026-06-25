import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface TaskCardProps {
  title: string;
  description: string;
  action?: string;
  onAction?: () => void;
}

export function TaskCard({ title, description, action = "Open", onAction }: TaskCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 p-4">
        <div>
          <p className="font-semibold">{title}</p>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        </div>
        {onAction ? <Button size="sm" variant="outline" onClick={onAction}>{action}</Button> : null}
      </CardContent>
    </Card>
  );
}
