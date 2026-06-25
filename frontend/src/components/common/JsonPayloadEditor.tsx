import { lazy, Suspense } from "react";
import { Copy } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/hooks/useToast";

const MonacoJsonViewer = lazy(() => import("./MonacoJsonViewer"));

export function JsonPayloadEditor({ title = "Payload preview", value, height = 420 }: { title?: string; value: unknown; height?: number }) {
  const toast = useToast();
  const json = JSON.stringify(value, null, 2);
  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
        <CardTitle>{title}</CardTitle>
        <Button
          variant="outline"
          size="sm"
          aria-label={`Copy ${title} JSON`}
          onClick={() => {
            navigator.clipboard?.writeText(json);
            toast.success("Payload copied", "JSON copied to clipboard");
          }}
        >
          <Copy className="h-4 w-4" />Copy
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        <Suspense fallback={<LoadingState label="Loading JSON viewer" className="min-h-[240px]" />}>
          <MonacoJsonViewer value={json} height={height} />
        </Suspense>
      </CardContent>
    </Card>
  );
}
