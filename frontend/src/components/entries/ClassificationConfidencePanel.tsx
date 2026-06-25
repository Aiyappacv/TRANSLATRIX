import type { FinancialEntry } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceBar } from "@/components/common/ConfidenceBar";

export function ClassificationConfidencePanel({ entry }: { entry: FinancialEntry }) {
  return (
    <Card>
      <CardHeader><CardTitle>Classification confidence</CardTitle><CardDescription>OCR confidence, classification confidence, SAP mapping confidence, and overall confidence.</CardDescription></CardHeader>
      <CardContent className="space-y-4">
        <ConfidenceBar label="OCR confidence" value={entry.confidence.ocr} />
        <ConfidenceBar label="Classification confidence" value={entry.confidence.classification} />
        <ConfidenceBar label="SAP mapping confidence" value={entry.confidence.mapping} />
        <ConfidenceBar label="Overall confidence" value={entry.confidence.overall} />
      </CardContent>
    </Card>
  );
}
