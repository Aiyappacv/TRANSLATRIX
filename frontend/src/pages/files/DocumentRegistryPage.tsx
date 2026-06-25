import { PageHeader } from "@/components/common/PageHeader";
import { DocumentRegistryTable } from "@/components/files/DocumentRegistryTable";

export function DocumentRegistryPage() {
  return (
    <>
      <PageHeader
        eyebrow="Document Extraction"
        title="Document Registry"
        description="Every document that has completed OCR/extraction, with confidence scores, processing metadata, and full audit history."
      />
      <DocumentRegistryTable />
    </>
  );
}
